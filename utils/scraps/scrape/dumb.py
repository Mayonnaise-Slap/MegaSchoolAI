import requests
from bs4 import BeautifulSoup


def dumb_parse(url: str) -> str:
    try:
        page = requests.get(url, timeout=10)
    except requests.exceptions.Timeout:
        print(f'Timed out: {url}')
        return ''

    if page.status_code != 200:
        return ""

    return BeautifulSoup(page.content, 'html.parser').get_text(' ', strip=True).lower()


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


def bounds_based_parse(url, bound=100):
    # FAIL
    # too long, exceeds context window
    data = dumb_parse(url)
    indexes = merge_sorted_indexes(list(find_all(data, 'итмо')), list(find_all(data, 'itmo')))
    surrounding = extract_surrounding(data, indexes, bound)
    return surrounding


def summarize_text(url: str, sdk, context: str) -> str:
    data = '\n'.join(bounds_based_parse(url))
    summarizer = sdk.models.completions('yandexgpt-lite').configure(temperature=0.3, max_tokens=2000)
    messages = [
        {
            "role": 'system',
            'text': f'Сократи предложенный текст, учитывая, что мне нужно извлечь из него информацию для ответа на следующий вопрос:\n{context}'
        }, {
            "role": 'user',
            "text": data[:min(8000, len(data))]
        }
    ]
    if data:
        text = summarizer.run(messages)[0].text
        return text
    return ''
