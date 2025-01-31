import asyncio
import json

import httpx
import requests

from test_cases import test_cases
from tests.test_cases import REMOTE_API_URL


async def send_request(session, data, request_id, API_URL):
    """Sends an async request to the app."""
    payload = json.dumps({"id": request_id, "query": data['question']}, ensure_ascii=False).encode("utf-8")
    try:
        response = await session.post(API_URL,
                                      data=payload,
                                      timeout=420,
                                      headers={"Content-Type": "application/json"})
        print(f"Response {request_id}: {response.status_code} - {'correct' if response.json()['answer'] == data['answer'] else 'wrong'}\n{response.text}")
    except Exception as e:
        print(f"Request {request_id} failed: {str(e)}")


async def test_concurrent_requests(API_URL, limit):
    """Sends 5 concurrent requests to the Flask API."""

    async with httpx.AsyncClient() as session:
        tasks = [send_request(session,
                              test_cases[i],
                              i,
                              API_URL) \
                 for i in range(min(len(test_cases), limit))]
        await asyncio.gather(*tasks)


def sync_test(API_URL):
    successes = 0
    for i, val in enumerate(test_cases[:5]):
        payload = json.dumps({"query": val["question"], 'id': i}, ensure_ascii=False).encode("utf-8")
        resource = requests.post(API_URL, data=payload)
        if resource.status_code == 200 and val["answer"] == resource.json()['answer']:
            successes += 1
            print(f"Success: {i} - {resource.text}")
        else:
            print(f"Failure: {i} - {resource.text}")


async def test_connection(API_URL):
    async with httpx.AsyncClient() as session:
        await send_request(session, test_cases[0]["question"], 0, API_URL)


# Run the test
if __name__ == '__main__':
    limit = 20
    asyncio.run(test_concurrent_requests(REMOTE_API_URL, limit))
