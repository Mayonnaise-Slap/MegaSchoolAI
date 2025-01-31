import json
from abc import ABC, abstractmethod
from typing import List, Tuple

from pydantic import BaseModel, Field, PrivateAttr, HttpUrl
from yandex_cloud_ml_sdk import YCloudML
from yandex_cloud_ml_sdk._models import Models

from schemas.request import PredictionResponse

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

    _sources_links: List[HttpUrl] = PrivateAttr()

    def answer(self) -> PredictionResponse:
        ya_gpt = self.sdk.models.completions('yandexgpt')

        error_handler = self.sdk.models.completions('yandexgpt-lite')

        ya_gpt.configure(temperature=self.temperature, max_tokens=2000)
        request_term = None

        try:
            _, dirty_request = self.__get_initial_data_request(ya_gpt)
            request_term = json.loads(dirty_request.strip())['query']
        except json.decoder.JSONDecodeError as e:
            print('Error parsing json')
            cap = 5
            counter = 0
            while not request_term and counter < cap:
                print(f'Entered fixing loop {counter}')
                counter += 1
                fixer_instructions = f"Here is an invalid json schema with json validator error. Return a repaired json object instead.\n{dirty_request}\n{e}"
                try:
                    dirty_request = error_handler.run(fixer_instructions)
                    request_term = json.loads(dirty_request.strip())['query']
                except json.decoder.JSONDecodeError as e:
                    continue
        except ValueError as e:
            print(e)

        print(request_term)

        return PredictionResponse(
            id=self.query_id,
            answer=1,
            reasoning="Из информации на сайте",
            sources=[HttpUrl('https://google.com')],
        )

    def __get_initial_data_request(self, model: Models) -> Tuple[str, str]:
        model_response = model.run(self._messages)

        print(model_response[0].text)

        return model_response[0].text.strip().split('---')


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

    api_key = os.getenv("YA_GPT_KEY")
    catalogue_id = os.getenv("YA_CATALOG_ID")

    sdk = YCloudML(
        folder_id=catalogue_id,
        auth=api_key,
    )
    question = "В каком году Университет ИТМО был включён в число Национальных исследовательских университетов России?\n1. 2007\n2. 2009\n3. 2011\n4. 2015"

    predictor = YaGPTResponse(query_id=1,
                              question=question,
                              sdk=sdk,
                              temperature=0.3)
    predictor.answer()
