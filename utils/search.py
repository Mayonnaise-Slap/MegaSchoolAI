import xml.etree.ElementTree as ET
from typing import List

import requests


def perform_search(query: str, folder_id: str, api_key: str) -> str:
    base_url = "https://yandex.ru/search/xml?sortby=rlv&filter=strict"
    auth_url = f"{base_url}&folderid={folder_id}&apikey={api_key}"

    response = requests.get(f'{auth_url}&query={query}')
    return response.text if response.status_code == 200 else ''


def parse_search(response_text: str) -> List[str]:
    if not response_text:
        return ['']
    root = ET.fromstring(response_text)
    urls = []
    for elem in root.findall(".//doc/*") + root.findall(".//properties/*"):
        if elem.tag == "url":
            urls.append(elem.text.strip())

    return urls


def get_search_urls(query: str, folder_id: str, api_key: str) -> List[str]:
    return parse_search(perform_search(query, folder_id, api_key))
