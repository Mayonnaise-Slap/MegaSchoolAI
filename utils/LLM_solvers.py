import json
from abc import ABC, abstractmethod
from typing import List

from pydantic import BaseModel, Field, PrivateAttr, HttpUrl
from yandex_cloud_ml_sdk import YCloudML
from yandex_cloud_ml_sdk._models import Models

from schemas.request import PredictionResponse
from search import search
from utils.exceptions import LLMWorkflowError
from utils.scraps.scrape.dumb import bounds_based_parse, summarize_text

with open('prompts/base_instruct.xml') as base_instructions:
    BASE_INSTRUCTIONS = base_instructions.read()

with open('prompts/after_search_instruct.xml') as after_search_instructions:
    AFTER_SEARCH_TEMPLATE = after_search_instructions.read()


class AbstractPredictionResponse(BaseModel, ABC):
    query_id: int = Field(..., description="Query ID")
    question: str = Field(..., description="Question from request")

    def __init__(self, **data):
        super().__init__(**data)
        self._messages = self.__get_initial_instructions

    @property
    def __get_initial_instructions(self) -> List[dict[str, str]]:
        return [
            {
                "role": "system",
                "text": BASE_INSTRUCTIONS,
            },
            {
                "role": "user",
                "text": f"{self.question}",
            },
        ]

    @abstractmethod
    def answer(self) -> PredictionResponse:
        pass

    class Config:
        arbitrary_types_allowed = True


class YaGPTResponse(AbstractPredictionResponse):
    sdk: YCloudML = Field(..., description="YaGPT SDK with credentials")
    temperature: float = Field(default=0.5, description="LLM temperature")
    search_api_key: str = Field(..., description="Yandex search API key")

    _sources_links: List[str] = PrivateAttr()
    _error_handler_prompt = [
        {
            "role": "system",
            "text": """I have a pseudo-json somewhere in the following text. Respond with a valid json from there. 
            use the following schema: {"query": "string"}""",
        }
    ]

    def answer(self) -> PredictionResponse:
        # models
        ya_gpt = self.sdk.models.completions('yandexgpt').configure(temperature=self.temperature, max_tokens=32000)
        error_handler = self.sdk.models.completions('yandexgpt-lite')

        # 1 step: get data sources
        dirty_data_request = self.__get_initial_data_request(ya_gpt)
        query_string = self.__handle_invalid_format(dirty_data_request, error_handler)

        print(query_string)

        self._sources_links = search(query_string,
                                     folder_id=self.sdk._folder_id,
                                     api_key=self.search_api_key)[:5]

        # 2 step: scrape data from sources
        # TODO update to be async
        scraped_data = {}

        print('scraping...')
        for i in self._sources_links:
            print('scraping', i)
            if attempt := summarize_text(i, sdk, self.question):
                scraped_data[i] = attempt
        after_search_instructions = AFTER_SEARCH_TEMPLATE.replace('{{ question_text }}', question)

        self._messages = [{
            "role": "system",
            'text': f"{after_search_instructions}\n",
        }, {
            "role": 'user',
            "text": f"# Факты и источники\n{scraped_data}"
        }]

        # 3 step: get final answer
        print('final elaborations\n\n___\n')
        print(ya_gpt.run(self._messages))

        return PredictionResponse(
            id=self.query_id,
            answer=1,
            reasoning="Из информации на сайте",
            sources=[HttpUrl('https://google.com')],
        )

    def __get_initial_data_request(self, model: Models) -> str:
        model_response = model.run(self._messages)
        self._messages.append({
            'role': 'system',
            'text': model_response[0].text,
        })

        print(model_response[0].text)

        return model_response[0].text

    @staticmethod
    def __handle_invalid_format(response: str, error_handler: Models) -> str:
        # 1 step: try naive approaches to extract json
        try:
            _, dirty_schema = response.split('---')
        except ValueError:
            guess_start = response.rfind('{')
            if guess_start == -1:
                dirty_schema = ''
            else:
                dirty_schema = response[guess_start:]

        # step 2: mix in a light llm to fix it for us
        if not dirty_schema:
            model_response = error_handler.run(response)
            dirty_schema = model_response[0].text

        # step 3: convert the possible text into a valid json, else restart the process
        try:
            json_object = json.loads(dirty_schema)
            return json_object['query']
        except json.decoder.JSONDecodeError:
            raise LLMWorkflowError('Failed to create a valid request')


if __name__ == '__main__':
    """
    V1: костыль
    Текущее состояние:
    обертка для подходов из mvp с очень грубой реализацией. 
    
    Задачи:
    Прикрутить поисковик наконец
    Обеспечить надежное исполнение запросов
    
    Варианты улучшения:
    Подключить нормальную агентную логику или RAG
    
    """
    import os

    from dotenv import load_dotenv

    load_dotenv()

    catalogue_id = os.getenv("YA_CATALOG_ID")
    gpt_api_key = os.getenv("YA_GPT_KEY")
    search_api_key = os.getenv("YA_SEARCH_KEY")

    sdk = YCloudML(
        folder_id=catalogue_id,
        auth=gpt_api_key,
    )
    question = "Сколько человек обучается итмо в 2021 году?\n1. 1500\n2. 14000\n3. 50000\n4. 19000"

    predictor = YaGPTResponse(query_id=1,
                              question=question,
                              sdk=sdk,
                              temperature=0.5,
                              search_api_key=search_api_key, )
    predictor.answer()
