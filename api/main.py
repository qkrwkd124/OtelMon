import os
import logging
from logging.handlers import RotatingFileHandler
import configparser
from collections.abc import Callable

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder

from routers import exporter


# 설정 파일 읽기
# base_dir = os.path.dirname(os.path.abspath(__file__))
# config = configparser.ConfigParser()
# config.read(os.path.join(base_dir,'database.conf'),encoding="utf-8")

# # log setting
# log_path = os.path.join(config['LOG']['log_path'],f"{config['LOG']['log_name']}.log")

# logging.basicConfig(
#     level=logging.INFO,
#     format='[%(asctime)s] %(process)d, "%(filename)s", %(lineno)d, %(funcName)s : %(message)s',datefmt='%Y/%m/%d %H:%M:%S',
#     handlers=[
#         RotatingFileHandler(log_path, maxBytes=10000000, backupCount=9)
#     ]
# )

app = FastAPI(title="OTLP Custom Exporter")
app.include_router(exporter.router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"], # 모든 HTTP 메소드 허용
    allow_headers=["*"], # 모든 헤더 허용
)

@app.get("/")
def test() :
    return {"message":"test"}

# container health 체크
@app.get("/health")
async def health_check():
    return {"status":"ok"}

# 요청 체크
@app.middleware("http")
async def log_request(request:Request, call_next:Callable) -> Response:
    """요청에 대한 로그"""
    logging.info(f"Request: {request.method} {request.url}")
    response: Response = await call_next(request)
    logging.info(f"Response: {response.status_code}")
    return response


# 422 에러를 처리하는 전역 예외 처리기
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):

    logging.error(f"Validation error for request {request.url}: {exc.errors()}")

    return JSONResponse(
        status_code=200,
        content={
            "status": "ERROR",
            "message": "Validation error for request",
            "result": ""
        }
    )

# 미확인된 예외 처리
@app.exception_handler(Exception)
async def exception_handler(request:Request, exc:Exception) -> JSONResponse:
    """예외 핸들러"""
    logging.error(f"Exception: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "status": "ERROR",
            "message": "알 수 없는 오류",
            "result": ""
        }
    )