import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from yandex_cloud_ml_sdk import YCloudML

from schemas.request import PredictionRequest, PredictionResponse
from utils.LLM_solvers import YaGPTResponse
from utils.exceptions import LLMWorkflowError
from utils.logger import setup_logger

# Initialize
app = FastAPI()
logger = setup_logger()

load_dotenv()

catalogue_id = os.getenv("YA_CATALOG_ID")
gpt_api_key = os.getenv("YA_GPT_KEY")
search_api_key = os.getenv("YA_SEARCH_KEY")


@app.on_event("startup")
async def startup_event():
    global logger
    logger = await setup_logger()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    body = await request.body()
    await logger.info(
        f"Incoming request: {request.method} {request.url}\n"
        f"Request body: {body.decode()}"
    )

    response = await call_next(request)
    process_time = time.time() - start_time

    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk

    await logger.info(
        f"Request completed: {request.method} {request.url}\n"
        f"Status: {response.status_code}\n"
        f"Response body: {response_body.decode()}\n"
        f"Duration: {process_time:.3f}s"
    )

    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )


@app.post("/api/request", response_model=PredictionResponse)
async def predict(body: PredictionRequest):
    try:
        await logger.info(f"Processing prediction request with id: {body.id}")

        sdk = YCloudML(
            folder_id=catalogue_id,
            auth=gpt_api_key,
        )

        for i in range(5):
            try:
                predictor = YaGPTResponse(query_id=body.id,
                                          question=body.query,
                                          sdk=sdk,
                                          temperature=0.3,
                                          search_api_key=search_api_key, )
                answer = await predictor.answer()
                await logger.info(f"Successfully processed request {body.id}")
                break
            except LLMWorkflowError as e:
                await logger.error(f"LLM workflow failed for request {body.id}: {e}, retrying {i + 1}")
                continue
            except ValueError as e:
                await logger.error(
                    f'LLM generated fake answer with invalid answer for request {body.id}: {e},  retrying {i + 1}')
        return answer
    except LLMWorkflowError as e:
        await logger.error(f"LLM workflow failed for request {body.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        await logger.error(f"Internal error processing request {body.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
