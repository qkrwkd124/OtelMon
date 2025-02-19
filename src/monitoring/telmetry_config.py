import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry import metrics

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
    otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317/v1/traces")
    
    # BatchSpanProcessor 에 OTLPSpanExporter 등록
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)
    
    # 트레이서 프로바이더 설정
    trace.set_tracer_provider(provider)

    return provider


def init_tracer():
    """
    OpenTelemetry 트레이서 초기화
    """
    resoure = Resource.create(attributes={"service.name": "etl_tracer", "service.version": "1.0.0","host.name": os.uname().nodename})
    
    tracer_provider = TracerProvider(resource=resoure)
    
    span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317/v1/traces"))
    
    tracer_provider.add_span_processor(span_processor)
    
    trace.set_tracer_provider(tracer_provider)
    
    return trace.get_tracer(__name__)

def init_meter():
    """
    OpenTelemetry 메트릭 초기화

    Returns:
        MeterProvider: 메트릭 프로바이더
    """
    
    otlp_metric_exporter = OTLPMetricExporter(endpoint="http://localhost:4317/v1/metrics")
    
    # 주기적으로 메트릭 데이터를 내보내는 MetricReader 생성
    metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter)
    
    # MeterProvider 생성
    provider = MeterProvider(metric_readers=[metric_reader])
    
    # 메트릭 프로바이더 설정
    
    return provider.get_meter(__name__)
