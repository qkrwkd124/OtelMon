import time
import traceback
from datetime import datetime
from dataclasses import dataclass, asdict
from functools import wraps
from typing import Dict, Any, Optional, Callable
import os

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from opentelemetry.instrumentation.requests import RequestsInstrumentor

import logging
import sys

# 로그 경로를 절대 경로로 설정
# log_path = "/opt/airflow/logs/trace_log.log"

# 로그 파일 핸들러 설정
# try:
#     file_handler = logging.FileHandler(log_path)
#     file_handler.setLevel(logging.DEBUG)  # DEBUG 레벨로 설정
#     formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     file_handler.setFormatter(formatter)

#     # stdout 핸들러 추가
#     stdout_handler = logging.StreamHandler(sys.stdout)
#     stdout_handler.setLevel(logging.DEBUG)
#     stdout_handler.setFormatter(formatter)

#     # 로그 설정
#     logger = logging.getLogger('trace_log')
#     logger.setLevel(logging.DEBUG)  # DEBUG 레벨로 설정
#     logger.addHandler(file_handler)
#     logger.addHandler(stdout_handler)
    
#     logger.debug("로그 핸들러 설정 완료")
# except Exception as e:
#     print(f"로그 설정 오류: {str(e)}")
#     traceback.print_exc()


@dataclass
class Result:
    """
    Airflow 작업의 결과를 저장하는 데이터 클래스
    
    Arguments
    ---------
    result : Dict[str, Any]
        작업 결과 데이터
    trace_metric : Dict[str, Any]
        트레이스에 기록할 메트릭 데이터
    process_count : int, 1
        처리한 결과 건수
    """
    result: Dict[str, Any]
    trace_metric: Dict[str, Any]
    process_count: int = 1


# 전역 변수로 선언
_tracer = None
_meter = None
_instrumented = False  # 자동 계측 초기화 여부 플래그
_span_processor = None


def _init_instrumentation():
    """자동 계측(Automatic Instrumentation) 설정"""
    global _instrumented
    if _instrumented:
        # 이미 한 번 초기화했다면 중복 호출 방지
        return
    
    # requests 자동 계측
    RequestsInstrumentor().instrument()
    
    _instrumented = True


def _init_tracer():
    """OpenTelemetry 트레이서 초기화"""
    global _tracer, _span_processor
    if _tracer is not None:
        # logger.debug("트레이서 이미 초기화됨")
        return _tracer
        
    resource = Resource.create(attributes={"service.name": "airflow_tracer", "service.version": "1.0.0","host.name": os.getenv('REAL_HOSTNAME','cpoetl'), "timezone": "Asia/Seoul"})
    tracer_provider = TracerProvider(resource=resource)
    # _span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otelcol:4317/v1/traces"))
    _span_processor = SimpleSpanProcessor(OTLPSpanExporter(endpoint="http://otelcol:4317/v1/traces"))
    tracer_provider.add_span_processor(_span_processor)
    trace.set_tracer_provider(tracer_provider)
    
    _tracer = trace.get_tracer(__name__)
    # logger.debug("트레이서 초기화 완료")
    return _tracer


def _init_meter():
    """OpenTelemetry 메트릭 초기화"""
    global _meter
    if _meter is not None:
        return _meter
    
    otlp_metric_exporter = OTLPMetricExporter(endpoint="http://otelcol:4317/v1/metrics")
    metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter)
    provider = MeterProvider(metric_readers=[metric_reader])
    
    _meter = provider.get_meter(__name__)
    return _meter


def traced_task(task_group: str = "default", **kwargs):
    """
    Airflow 작업에 대한 OpenTelemetry 트레이싱 데코레이터
    
    Arguments:
    ----------
    task_group: str
        작업이 속한 그룹 이름
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                tracer = _init_tracer()
                meter = _init_meter()
                _init_instrumentation()
                
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
                        
                        group_name = kwargs.get("group_name", task_group)
                        process_name = func.__name__
                        
                        # 기본 span 속성 설정
                        span.set_attribute("etl.platform", "Airflow")
                        span.set_attribute("etl.group_name", group_name)
                        span.set_attribute("etl.process_name", process_name)
                        
                        # 추가 키워드 인수를 span 속성으로 설정
                        for key, value in kwargs.items():
                            if isinstance(value, (str, int, float, bool)):
                                span.set_attribute(f"etl.{key}", str(value))
                        
                        # 프로세스 시작 시간 기록
                        span.set_attribute("etl.start_time", start_time.isoformat())
                        
                        # 함수 실행
                        result = func(*args, **kwargs)

                        # logger.debug(f"함수 실행 완료: {func.__name__}")
                        
                        # 프로세스 종료 시간 및 duration 기록
                        end_time = datetime.now()
                        duration = (end_time - start_time).total_seconds()
                        
                        # 결과를 속성으로 기록
                        if isinstance(result, Result):
                            span.set_attribute("etl.process_count", result.process_count)
                            for key, value in result.trace_metric.items():
                                span.set_attribute(f"{key}", str(value))
                        
                        # 메트릭 기록
                        process_counter.add(1, {"status": "success"})
                        duration_histogram.record(duration)
                        
                        # 명시적으로 성공 상태 설정
                        span.set_status(StatusCode.OK,"성공적으로 완료되었습니다.")
                        
                        # 성공 이벤트 추가
                        span.add_event("process_completed", {
                            "result": "success",
                            "duration": str(duration)
                        })
                        
                        return result
                        
                    except Exception as e:
                        # 오류 정보 기록
                        error_msg = traceback.format_exc()
                        span.set_attribute("etl.error", error_msg)
                        span.set_attribute("etl.error_type", type(e).__name__)
                        span.set_attribute("etl.stacktrace", error_msg)
                        
                        # 오류 메트릭 기록
                        process_counter.add(1, {"status": "error"})
                        
                        # 오류 상태 설정
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        
                        # 예외 기록
                        span.record_exception(e)
                        
                        raise
                        
                    finally:
                        # 종료 시간 기록
                        span.set_attribute("etl.end_time", datetime.now().isoformat())
            
            except Exception as e:
                # OpenTelemetry 관련 오류가 발생하더라도 원래 함수는 실행
                return func(*args, **kwargs)
        
        return wrapper
    return decorator
