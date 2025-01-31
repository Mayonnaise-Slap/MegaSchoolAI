import asyncio
import aiohttp
from bs4 import BeautifulSoup
from yandex_cloud_ml_sdk import YCloudML


async def dumb_parse(url: str) -> str:
    """Asynchronously fetches and parses webpage content into plain text."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    return ""
                content = await response.text(errors='replace')
    except asyncio.TimeoutError:
        # print(f'Timed out: {url}')
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


def extract_surrounding(source, indexes, bound=100):
    result = []
    while indexes:
        center = indexes.pop(0)
        start, end = max(0, center - bound), min(len(source), center + bound)
        while indexes and indexes[0] - (2 * bound) < end:
            center = indexes.pop(0)
            end = min(len(source), center + bound)
        result.append(source[start:end])
    return '\n'.join(result)


async def bounds_based_parse(url, bound=100):
    data = await dumb_parse(url)
    indexes = merge_sorted_indexes(list(find_all(data, 'итмо')), list(find_all(data, 'itmo')))
    surrounding = extract_surrounding(data, indexes, bound)
    return surrounding


async def summarize_text(url: str, sdk, context: str) -> str:
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

async def process_all_sources(sources, sdk, question):
    """Runs `summarize_text` concurrently for multiple sources."""
    tasks = [summarize_text(url, sdk, question) for url in sources]
    results = await asyncio.gather(*tasks)
    return {url: result for url, result in zip(sources, results)}


if __name__ == '__main__':
    sources = ["https://itmo.ru/", "https://itmo.ru/ru/page/207/ob_universitete.htm", "https://ru.wikipedia.org/wiki/%D0%A3%D0%BD%D0%B8%D0%B2%D0%B5%D1%80%D1%81%D0%B8%D1%82%D0%B5%D1%82_%D0%98%D0%A2%D0%9C%D0%9E"]
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
    results = asyncio.run(process_all_sources(sources, sdk, question))
    # print(results)