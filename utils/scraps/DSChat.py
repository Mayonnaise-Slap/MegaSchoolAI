# -*- coding: utf-8 -*-

import os

from dotenv import load_dotenv
from yandex_cloud_ml_sdk import YCloudML

from chat_history import chat_history

load_dotenv()

api_key = os.getenv("YA_GPT_KEY")
catalogue_id = os.getenv("YA_CATALOG_ID")

# with open('prompts/base_instruct.xml') as inst:
#     BASE_INSTRUCTIONS = inst.read()
#
# messages = [
#     {
#         "role": "system",
#         "text": BASE_INSTRUCTIONS,
#     },
#     {
#         "role": "user",
#         "text": "В каком рейтинге (по состоянию на 2021 год) ИТМО впервые вошёл в топ-400 мировых университетов?\n1. ARWU (Shanghai Ranking)\n2. Times Higher Education (THE) World University Rankings\n3. QS World University Rankings\n4. U.S. News & World Report Best Global Universities",
#     },
# ]
messages = chat_history

sdk = YCloudML(
    folder_id=catalogue_id,
    auth=api_key,
)


def main():
    model = sdk.models.completions("yandexgpt")
    model = model.configure(temperature=0.5)
    result = model.run(messages)

    for alternative in result:
        print(alternative.text)

"""
Текущее состояние: 
Я могу вручную создавать запросы и вводить ссылки из поисковика
"""
# TODO прикрутить поисковиковый API
# TODO прикрутить весь ризонинг в 1 функцию/класс
# TODO написать тестов
# TODO оценка стоимости

if __name__ == "__main__":
    main()
