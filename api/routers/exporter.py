import logging
import json
import gzip

from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Depends
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2
from opentelemetry.proto.trace.v1 import trace_pb2
from google.protobuf.json_format import MessageToDict

from logger import get_logger
from config import get_settings
from utils.trace_processor import extract_process_executions
from services.notification import NotificationService

router = APIRouter()
logger = get_logger(__name__)

def get_db_service():
    pass

def get_notification_service():
    return NotificationService(get_settings())

@router.post("/exporter/v1/traces")
async def export_telemetry_data(
    request:Request,
    background_tasks:BackgroundTasks,
    # db_service = Depends(get_db_service),
    notification_service:NotificationService = Depends(get_notification_service),
):
    """
    OTLP Collector가 POST 방식으로 전송한 텔레메트리 데이터를 수신하는 엔드포인트.
    """
    try :
        # 압축된 데이터 수신
        compressed_content = await request.body()

        # 헤더 정보 출력
        logger.info(f"Headers: {dict(request.headers)}")

        # 압축 형식 확인
        content_encoding = request.headers.get("content-encoding", "").lower()
        logger.info(f"Content-Encoding: {content_encoding}")

        # 압축 해제
        if content_encoding == "gzip" or compressed_content.startswith(b"\x1f\x8b\x08") :
            content = gzip.decompress(compressed_content)
        else :
            content = compressed_content

        # 데이터 미리보기
        logger.info(f"Content preview: {content[:50]}")
        
        # protobuf 데이터 파싱
        trace_data = trace_service_pb2.ExportTraceServiceRequest()
        trace_data.ParseFromString(content)
        
        # protobuf 메시지를 dict로 변환
        json_data = MessageToDict(trace_data)
        
        # 디버깅을 위한 로그
        logger.info(f"Received content type: {request.headers.get('content-type')}")
        logger.info(f"Raw content length: {len(content)}")
        # logger.info(f"Converted JSON data: {json.dumps(json_data, ensure_ascii=False, indent=2)}")

        execution_data_list = extract_process_executions(json_data)

        logger.info(f"Extracted execution data: {execution_data_list}")

        # 실패한 작업에 대해 알림 발송
        for execution_data in execution_data_list:
            if not execution_data.get("success", True):
                background_tasks.add_task(notification_service.notify_failure, execution_data)
                logger.info('mail send')
        return {"status": "success", "data": json_data}

    except Exception as e :
        logger.error(f"Error parsing trace data: {str(e)}")
        return {"status": "error", "message": str(e)}
