import asyncio
import json

import httpx
import requests

API_URL = 'http://localhost:8080/api/request'

test_cases = [
    {
        "question": "В каком городе находится главный кампус Университета ИТМО?\n1. Москва\n2. Санкт-Петербург\n3. Екатеринбург\n4. Нижний Новгород",
        "answer": 2},
    {"question": "Сколько человек обучается в итмо?\n1. Москва\n2. 1900\n3. 16000\n4. 25000", "answer": 3},
    {"question": "Как сейчас называется университет?\n1. ЛИТМО\n2. Санкт-Петербург\n3. СПБГУ\n4. ИТМО", "answer": 4},
    {"question": "Сколько образовательных программ в бакалавриате ИТМО?\n1. 26\n2. 12\n3. 100\n4. 20", "answer": 1},
    {
        "question": "Какое из следующих достижений позволит поступить в магистратуру итмо по БВИ?\n1. победа в МегаШколе\n2. Наличие паспорта\n3. победа в конкурсе `самые чистые ноздри`\n4. Высшая проба",
        "answer": 1},
    {
        "question": "По какому адресу находится корпус итмо на ломоносова?\n1. улица Ломоносова, 9\n2. Биржевая линия, 14\n3. Вашингтон\n4.  улица Ломоносова, 22",
        "answer": 1},
    {
        "question": "Какого факультета нет в итмо?\n1. Физико-технический мегафакультет\n2. Мегафакультет наук о жизни\n3. Факультет систем управления и робототехники\n4. Факультет экономики и финансов",
        "answer": 4},
]


async def send_request(session, data, request_id):
    """Sends an async request to the Flask app."""
    payload = json.dumps({"id": request_id, "query": data}, ensure_ascii=False).encode("utf-8")
    try:
        response = await session.post(API_URL, data=payload, timeout=20)
        print(f"Response {request_id}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Request {request_id} failed: {e}")


async def test_concurrent_requests():
    """Sends 5 concurrent requests to the Flask API."""

    async with httpx.AsyncClient() as session:
        tasks = [send_request(session, test_cases[i]["question"], i) for i in range(5)]
        await asyncio.gather(*tasks)


def sync_test():
    successes = 0
    for i, val in enumerate(test_cases[:5]):
        payload = json.dumps({"query": val["question"], 'id': i}, ensure_ascii=False).encode("utf-8")
        resource = requests.post(API_URL, data=payload)
        if resource.status_code == 200 and val["answer"] == resource.json()['answer']:
            successes += 1
            print(f"Success: {i} - {resource.text}")
        else:
            print(f"Failure: {i} - {resource.text}")




# Run the test
if __name__ == '__main__':
    asyncio.run(test_concurrent_requests())
    # sync_test()
