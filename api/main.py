import os
import logging
from logging.handlers import RotatingFileHandler
import configparser
import uuid
import time
from collections.abc import Callable

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder

from routers import exporter
from logger import app_logger

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
    """요청 로깅 미들웨어"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    app_logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={"request_id": request_id}
    )
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    app_logger.info(
        f"Request completed: {request.method} {request.url.path} "
        f"Status: {response.status_code} Duration: {process_time:.3f}s",
        extra={"request_id": request_id}
    )
    
    response.headers["X-Request-ID"] = request_id
    return response



# 422 에러를 처리하는 전역 예외 처리기
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):

    app_logger.error(f"Validation error for request {request.url}: {exc.errors()}")

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
    app_logger.error(f"Exception: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "status": "ERROR",
            "message": "알 수 없는 오류",
            "result": ""
        }
    )