import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

def init_telemetry():

    # 전역 TracerProvider 설정
    provider = TracerProvider()

    # Exporter 등록(예: 콘솔)
    console_exporter = ConsoleSpanExporter()
    span_processor = BatchSpanProcessor(console_exporter)
    provider.add_span_processor(span_processor)

    trace.set_tracer_provider(provider)
    
    return provider
    

def init_telemetry_otlp():
    """
    OTLP 프로토콜로 데이터를 전송하는 트레이서 초기화

    Returns:
        TracerProvider: 트레이서 프로바이더
    """
    resoure = Resource.create(attributes={"service.name": "etl_tracer", "service.version": "1.0.0","host.name": os.uname().nodename})
    
    # 트레이서 프로바이더 생성
    provider = TracerProvider(resource=resoure)
    
    # 스팬 프로세서 생성
    otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")
    
    # BatchSpanProcessor 에 OTLPSpanExporter 등록
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)
    
    # 트레이서 프로바이더 설정
    trace.set_tracer_provider(provider)

    return provider


