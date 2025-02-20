import time
import traceback
from datetime import datetime
from dataclasses import dataclass, asdict
from functools import wraps
from typing import Dict, Any
import os

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource


@dataclass
class Result():
    """
    NiFi 프로세스의 return에 대한 데이터 클래스 입니다.

    Arguments
    ---------
    result : Dict[str, Any]
        NiFi의 Attribute로 전달될 데이터입니다.
        키는 Attribute의 키가 되고 값은 Attribute의 값이 됩니다
    process_count : int, 1
        처리한 결과 건 수입니다.
    """
    result: Dict[str, Any]
    trace_metric: Dict[str, Any]
    process_count: int = 1
    
# 전역 변수로 선언
_tracer = None
_meter = None

def _init_tracer():
    """
    OpenTelemetry 트레이서 초기화
    """
    global _tracer
    if _tracer is not None:
        return _tracer
        
    resoure = Resource.create(attributes={"service.name": "etl_tracer", "service.version": "1.0.0","host.name": os.uname().nodename})
    tracer_provider = TracerProvider(resource=resoure)
    span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317/v1/traces"))
    tracer_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(tracer_provider)
    
    _tracer = trace.get_tracer(__name__)
    return _tracer

def _init_meter():
    """
    OpenTelemetry 메트릭 초기화
    """
    global _meter
    if _meter is not None:
        return _meter
        
    otlp_metric_exporter = OTLPMetricExporter(endpoint="http://localhost:4317/v1/metrics")
    metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter)
    provider = MeterProvider(metric_readers=[metric_reader])
    
    _meter = provider.get_meter(__name__)
    return _meter


def traced(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        
        tracer = _init_tracer()
        meter = _init_meter()
        
        # 메트릭 카운터와 히스토그램 생성
        process_counter = meter.create_counter(
            name="etl_process_count",
            description="ETL 프로세스 실행 횟수",
            unit="1"
        )
        duration_histogram = meter.create_histogram(
            name="etl_duration",
            description="ETL 프로세스 실행 시간",
            unit="s"
        )
        
        with tracer.start_as_current_span(func.__name__) as span:
            try:
                start_time = datetime.now()
                
                # 프로세스 시작 시간 기록
                span.set_attribute("etl.start_time", start_time.isoformat())
                span.set_attribute("etl.process_name", func.__name__)
                
                # 함수 실행
                result = func(*args, **kwargs)
                
                # 프로세스 종료 시간 및 duration 기록
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # 스팬에 결과 기록
                if isinstance(result, Result):
                    span.set_attribute("etl.process_count", result.process_count)
                    span.set_attribute("etl.success", True)
                    for key, value in result.trace_metric.items():
                        span.set_attribute(f"{key}", str(value))
                
                # 메트릭 기록
                process_counter.add(1, {"status": "success"})
                duration_histogram.record(duration)
                
                span.set_status(StatusCode.OK)
                return result
                
            except Exception as e:
                # 오류 정보 기록
                span.set_attribute("etl.error", str(e))
                span.set_attribute("etl.error_type", type(e).__name__)
                span.set_attribute("etl.stacktrace", traceback.format_exc())
                span.set_attribute("etl.success", False)
                
                # 오류 메트릭 기록
                process_counter.add(1, {"status": "error"})
                
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
                
            finally:
                # 종료 시간 기록
                span.set_attribute("etl.end_time", datetime.now().isoformat())
    
    return wrapper


