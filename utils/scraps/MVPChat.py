# -*- coding: utf-8 -*-

import os

from dotenv import load_dotenv
from yandex_cloud_ml_sdk import YCloudML

# from chat_history import chat_history

load_dotenv()

api_key = os.getenv("YA_GPT_KEY")
catalogue_id = os.getenv("YA_CATALOG_ID")

with open('../prompts/base_instruct.xml') as inst:
    BASE_INSTRUCTIONS = inst.read()

messages = [
    {
        "role": "system",
        "text": BASE_INSTRUCTIONS,
    },
    {
        "role": "user",
        "text": "В каком году Университет ИТМО был включён в число Национальных исследовательских университетов России?\n1. 2007\n2. 2009\n3. 2011\n4. 2015",
    },
]
# messages = chat_history

sdk = YCloudML(
    folder_id=catalogue_id,
    auth=api_key,
)


def main():
    model = sdk.models.completions("yandexgpt")
    model = model.configure(temperature=0.8)
    result = model.run(messages)

    for alternative in result:
        print(alternative.text)


"""
V0: MVP
Текущее состояние: 
Я могу вручную создавать запросы и вводить ссылки из поисковика
"""
# TODO прикрутить поисковиковый API
# TODO написать тестов

if __name__ == "__main__":
    main()
