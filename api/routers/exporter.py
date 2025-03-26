import logging
import json

from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2
from opentelemetry.proto.trace.v1 import trace_pb2
from google.protobuf.json_format import MessageToDict


router = APIRouter()

@router.post("/exporter/v1/traces")
async def export_telemetry_data(request:Request, background_tasks:BackgroundTasks):
    """
    OTLP Collector가 POST 방식으로 전송한 텔레메트리 데이터를 수신하는 엔드포인트.
    """
    try :
        # protobuf 형식의 바이너리 데이터 수신
        content = await request.body()
        
        # protobuf 데이터 파싱
        trace_data = trace_service_pb2.ExportTraceServiceRequest()
        trace_data.ParseFromString(content)
        
        # protobuf 메시지를 dict로 변환
        json_data = MessageToDict(trace_data)
        
        # 디버깅을 위한 로그
        print(f"Received content type: {request.headers.get('content-type')}")
        print(f"Raw content length: {len(content)}")
        print(f"Converted JSON data: {json.dumps(json_data, indent=2)}")
        
        return {"status": "success", "data": json_data}

    except Exception as e :
        print(f"Error parsing trace data: {str(e)}")
        return {"status": "error", "message": str(e)}
