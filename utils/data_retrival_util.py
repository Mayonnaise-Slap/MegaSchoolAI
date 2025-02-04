import asyncio
from typing import List, Dict

import aiohttp
from bs4 import BeautifulSoup
from yandex_cloud_ml_sdk import YCloudML


async def dumb_parse(url: str) -> str:
    """Асинхронно запрашивает html страницы и
    парсит его в блок текста"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    return ""
                content = await response.text(errors='replace')
    except asyncio.TimeoutError:
        return ''

    return BeautifulSoup(content, 'html.parser').get_text(' ', strip=True).lower()


def merge_sorted_indexes(list1, list2):
    merged = []
    i, j = 0, 0
    while i < len(list1) and j < len(list2):
        if list1[i] < list2[j]:
            merged.append(list1[i])
            i += 1
        else:
            merged.append(list2[j])
            j += 1
    merged.extend(list1[i:])
    merged.extend(list2[j:])
    return merged


def find_all(a_str, sub):
    start = 0
    while True:
        start = a_str.find(sub, start)
        if start == -1: return
        yield start
        start += len(sub)


def extract_surrounding(source: str, indexes: List[int], bound=100) -> str:
    """Извлекает подстроки вокруг слов итмо"""
    result = []
    while indexes:
        center = indexes.pop(0)
        start, end = max(0, center - bound), min(len(source), center + bound)
        while indexes and indexes[0] - (2 * bound) < end:
            center = indexes.pop(0)
            end = min(len(source), center + bound)
        result.append(source[start:end])
    return '\n'.join(result)


async def bounds_based_parse(url: str, bound: int = 100) -> str:
    """
    Наивный подход для извлечения контекстных данных:
    берет 2 * bound символов вокруг слов итмо и itmo
    и возвращает одним текстовым блоком. Для классического
    nlp еще бы нормализовать, но llm не очень такое любит
    """
    data = await dumb_parse(url)
    indexes = merge_sorted_indexes(list(find_all(data, 'итмо')), list(find_all(data, 'itmo')))
    surrounding = extract_surrounding(data, indexes, bound)
    return surrounding


async def summarize_text(url: str, sdk, context: str) -> str:
    """
    Функция берет дамп текста со страницы и отправляет его в llm для
    суммаризации / извлечения фактов
    """
    data = await bounds_based_parse(url)
    if not data:
        return ""

    summarizer = sdk.models.completions('yandexgpt-lite').configure(temperature=0.3, max_tokens=4000)
    messages = [
        {
            "role": 'system',
            'text': f'Сократи предложенный текст, учитывая, что мне нужно извлечь из него информацию для ответа на следующий вопрос:\n{context}'
        },
        {
            "role": 'user',
            "text": data[:min(8000, len(data))]
        }
    ]

    text = summarizer.run(messages)[0].text
    return text


async def process_all_sources(sources: List[str], sdk: YCloudML, question_context: str) -> Dict[str, str]:
    """
    Асинхронная функция для асинхронного скрейпинга и суммаризации веб страниц
    """
    tasks = [summarize_text(url, sdk, question_context) for url in sources]
    summarizations = await asyncio.gather(*tasks)
    return {url: result for url, result in zip(sources, summarizations)}
