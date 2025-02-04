import asyncio
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Union

from pydantic import BaseModel, Field, PrivateAttr
from yandex_cloud_ml_sdk import YCloudML
from yandex_cloud_ml_sdk._models import Models

from schemas.request import PredictionResponse
from utils.cleanup import get_cleanup_prompt
from utils.data_retrival_util import process_all_sources
from utils.exceptions import LLMWorkflowError
from utils.search import get_search_urls


with open('utils/prompts/base_instruct.xml') as base_instructions:
    BASE_INSTRUCTIONS = base_instructions.read()

with open('utils/prompts/after_search_instruct.xml') as after_search_instructions:
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
        arbitrary_types_allowed = True  # для удовлетворения lsp PyCharm'а


class YaGPTResponse(AbstractPredictionResponse):
    sdk: YCloudML = Field(..., description="YaGPT SDK with credentials")
    temperature: float = Field(default=0.5, description="LLM temperature")
    search_api_key: str = Field(..., description="Yandex search API key")

    _sources_links: List[str] = PrivateAttr()

    async def answer(self) -> PredictionResponse:
        """
        Точка входа в workflow, отсюда класс управляет собой сам
        """
        # models
        ya_gpt = self.sdk.models.completions('yandexgpt-lite').configure(temperature=self.temperature, max_tokens=32000)
        error_handler = self.sdk.models.completions('yandexgpt-lite')

        # 1 step: get data sources
        dirty_data_request = self.__get_initial_data_request(ya_gpt)
        query_string = self.__handle_invalid_format(dirty_data_request, error_handler)

        self._sources_links = get_search_urls(query_string,
                                              folder_id=self.sdk._folder_id,
                                              api_key=self.search_api_key)[:4]

        # 2 step: scrape data from sources
        future = asyncio.create_task(process_all_sources(self._sources_links, self.sdk, self.question))
        scraped_data = await future
        after_search_instructions = AFTER_SEARCH_TEMPLATE.replace('{{ question_text }}', self.question)

        self._messages = [{
            "role": "system",
            'text': f"{after_search_instructions}\n",
        }, {
            "role": 'user',
            "text": f"# Факты и источники\n{scraped_data}\nОтветь на мой вопрос: {self.question}",
        }]

        # 3 step: get final answer
        dirty_response = ya_gpt.run(self._messages)[0].text
        clean_response = self.__parse_invalid_final_response(dirty_response, error_handler)
        answer = clean_response['answer']

        if type(answer) == str and answer.isalnum():
            answer = int(answer)
        if type(answer) != int:
            answer = -1

        return PredictionResponse(
            id=self.query_id,
            answer=answer,
            reasoning=clean_response['reasoning'],
            sources=clean_response['sources'][:3],
        )

    def __get_initial_data_request(self, model: BaseModel) -> str:
        """
        Приватная функция, получает из llm запрос на данные в поисковике
        """
        model_response = model.run(self._messages)
        self._messages.append({
            'role': 'assistant',
            'text': model_response[0].text,
        })

        return model_response[0].text

    def __handle_invalid_format(self, response: str, error_handler: Models) -> str:
        """
        Приватная функция для извлечения поискового запроса из ответа llm
        """
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
            prompt = get_cleanup_prompt(schema="""{"query": "query_text"}""", dirty_text=response)
            model_response = error_handler.run(prompt)
            dirty_schema = model_response[0].text

        # step 3: second naive pass
        guess_start = dirty_schema.rfind('{')
        guess_end = dirty_schema.rfind('}')
        if guess_start == -1:
            dirty_schema = ''
        else:
            dirty_schema = dirty_schema[guess_start:guess_end + 1]

        # step 4: convert the possible text into a valid json, else restart the process
        try:
            json_object = json.loads(dirty_schema)
            return json_object['query']
        except json.decoder.JSONDecodeError:
            raise LLMWorkflowError('Failed to create a valid request')

    def __parse_invalid_final_response(self, response: str, error_handler: Models) -> Dict[str, Union[str, List[str]]]:
        """
        Приватная функция для парсинга вывода workflow в валидную json схему
        """
        # 1 step: try naive approaches to extract json
        try:
            _, dirty_schema = response.split('---')
        except ValueError:
            guess_start = response.rfind('{')
            guess_end = response.rfind('}')
            if guess_start == -1:
                dirty_schema = ''
            else:
                dirty_schema = response[guess_start:guess_end + 1]

        # step 2: mix in a light llm to fix it for us
        if not dirty_schema:
            prompt = get_cleanup_prompt(
                schema="""{"answer": "text", "reasoning": "text", "sources": ["text", "text"]}""", dirty_text=response)
            model_response = error_handler.run(prompt)
            dirty_schema = model_response[0].text

        # step 3: second naive pass
        guess_start = dirty_schema.rfind('{')
        guess_end = dirty_schema.rfind('}')
        if guess_start == -1:
            dirty_schema = ''
        else:
            dirty_schema = dirty_schema[guess_start:guess_end + 1]
        # step 4: convert the possible text into a valid json, else restart the process
        try:
            return json.loads(dirty_schema)
        except json.decoder.JSONDecodeError:
            raise LLMWorkflowError('Failed to create a valid request')
