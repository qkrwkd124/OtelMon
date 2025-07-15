import time
import traceback
from datetime import datetime
from dataclasses import dataclass, asdict, field
from functools import wraps
from typing import Dict, Any, Callable, Optional
from pathlib import Path
import inspect
import os
from enum import Enum

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Span
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from module.system_info import SimpleSystemInfo

class Platform(Enum):
    """지원되는 플랫폼"""
    NIFI = "NiFi"
    AIRFLOW = "Airflow"

@dataclass
class Result:
    """
    NiFi 프로세스의 return에 대한 데이터 클래스 입니다.

    Arguments
    ---------
    result : Dict[str, Any]
        NiFi의 Attribute로 전달될 데이터입니다.
        키는 Attribute의 키가 되고 값은 Attribute의 값이 됩니다
    trace_attributes : Dict[str, Any]
        트레이스에 기록할 메트릭 데이터입니다.
    process_count : int, 1
        처리한 결과 건 수입니다.
    """
    result: Dict[str, Any]
    process_count: int = 0
    trace_attributes: Dict[str, Any] = field(default_factory=dict)
    source_info: Optional[SimpleSystemInfo] = None
    target_info: Optional[SimpleSystemInfo] = None

    def to_nifi_result(self):
        """
        현재 trace_log.Result 객체를 nifi.Result 객체로 변환합니다.
        
        Returns:
            nifi.Result: nifi 모듈의 Result 객체
        """
        # 동적 임포트를 사용하여 circular import 방지
        import module.nifi as nifi
        
        # nifi.Result 생성 및 반환
        return nifi.Result(
            result=self.result,
            process_count=self.process_count
        )
    
    def to_airflow_result(self):
        """
        Airflow TaskFlow API에서 사용할 수 있는 딕셔너리 형태로 변환
        
        Returns:
            Dict[str, Any]: Airflow에서 사용할 결과 딕셔너리
        """
        return self.result

# 전역 변수로 선언
_tracer_initialized = False 
_instrumented = False

# 설정 상수
SERVICE_NAME = "etl_tracer"
SERVICE_VERSION = "1.0.0"
OTEL_ENDPOINT = "http://otelcol:4317/v1/traces"


def _init_instrumentation():
    """자동 계측(Automatic Instrumentation) 설정"""
    global _instrumented
    if _instrumented:
        # 이미 한 번 초기화했다면 중복 호출 방지
        return
    
    # requests 자동 계측
    RequestsInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    _instrumented = True


def _init_tracer():
    """
    OpenTelemetry 트레이서 초기화
    
    Returns:
        트레이서 객체
    """
    global _tracer_initialized
    # 이미 초기화되었다면 기존 tracer 반환
    if _tracer_initialized:
        return trace.get_tracer(__name__)
    
    # 리소스 및 트레이서 설정    
    resource = Resource.create(attributes={
        "service.name": SERVICE_NAME, 
        "service.version": SERVICE_VERSION,
        "host.name": os.getenv('REAL_HOSTNAME', 'cpietl'), 
        "timezone": "Asia/Seoul"
    })
    
    tracer_provider = TracerProvider(resource=resource)

    
    # 실행 환경에 따라 SpanProcessor 선택
    # NiFi : 지속적인 JVM 프로세스에서 실행하여 BatchSpanProcessor가 span을 전송할 충분한 시간이 있음
    # Airflow : 각 태스크가 독립적인 프로세스로 실행 span을 전송하기 전에 프로세스가 종료되어 span이 손실됨.
    if os.getenv('AIRFLOW_HOME'):  # Airflow 환경 감지
        # Airflow: 즉시 전송하는 SimpleSpanProcessor 사용
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        span_processor = SimpleSpanProcessor(
            OTLPSpanExporter(endpoint="http://otelcol:4317/v1/traces")
        )
    else:
        # NiFi: 배치 전송하는 BatchSpanProcessor 사용
        span_processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint="http://otelcol:4317/v1/traces"),
            max_queue_size=2048,            # 큐 크기
            schedule_delay_millis=5000,     # 5초마다 배치 전송
            max_export_batch_size=512,      # 배치 크기
            export_timeout_millis=30000     # 전송 타임아웃 30초
        )

    tracer_provider.add_span_processor(span_processor)
    # 전역 TracerProvider 설정 (OpenTelemetry 내부 싱글톤)
    trace.set_tracer_provider(tracer_provider)

    _tracer_initialized = True
    
    # 전역 TracerProvider에서 tracer 가져오기
    return trace.get_tracer(__name__)


def _record_span_attributes(span: Span, result: Result):
    """
    스팬에 결과 속성 기록
    
    Arguments:
    ----------
    span : Span
        현재 스팬 객체
    result : Result
        함수 실행 결과
    """
    if isinstance(result, Result):
        span.set_attribute("etl.process_count", result.process_count)
        for key, value in result.trace_attributes.items():
            span.set_attribute(f"{key}", str(value))

def _record_system_info(span: Span,  source: Optional[SimpleSystemInfo]=None, target: Optional[SimpleSystemInfo]=None):
    """
    시스템 정보 기록
    
    Arguments:
    ----------
    span : Span
        현재 스팬 객체
    source : Optional[SimpleSystemInfo]
        소스 시스템 정보
    target : Optional[SimpleSystemInfo]
        타겟 시스템 정보
    """
    if source:
        for key, value in asdict(source).items():
            if value is not None:  # None 값은 기록하지 않음
                span.set_attribute(f"etl.source_{key}", str(value))
    if target:
        for key, value in asdict(target).items():
            if value is not None:  # None 값은 기록하지 않음
                span.set_attribute(f"etl.target_{key}", str(value))


def _record_error(span: Span, error: Exception):
    """
    스팬에 오류 정보 기록
    
    Args:
        span: 현재 스팬 객체
        error: 발생한 예외
    """
    span.set_attribute("etl.error", str(error))
    span.set_attribute("etl.error_type", type(error).__name__)
    span.set_attribute("etl.stacktrace", traceback.format_exc())
    span.set_status(Status(StatusCode.ERROR, str(error)))
    span.record_exception(error)


def traced(group_name="ETL NiFi", platform:Platform = Platform.NIFI):
    """
    OpenTelemetry 트레이싱 데코레이터
    
    Args:
        group_name: 작업이 속한 그룹 이름
        
    Returns:
        데코레이터 함수
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = _init_tracer()
            _init_instrumentation()
            
            with tracer.start_as_current_span(func.__name__) as span:
                start_time = datetime.now()
                
                # 기본 속성 설정
                func_filename = Path(inspect.getfile(func)).name
                process_name = kwargs.get("nifi_process_name", kwargs.get("process_name", func.__name__))
                span.set_attribute("etl.platform", platform.value)
                span.set_attribute("etl.group_name", kwargs.get("group_name", group_name))
                span.set_attribute("etl.process_name", process_name)
                span.set_attribute("etl.script_name", func_filename)
                span.set_attribute("etl.start_time", start_time.isoformat())
                
                try:
                    # 함수 실행
                    result = func(*args, **kwargs)
                    
                    # 결과 기록
                    if isinstance(result, Result):
                        _record_span_attributes(span, result)
                        _record_system_info(span, result.source_info, result.target_info)
                        
                        # trace_log.Result를 nifi.Result로 변환

                        if platform == Platform.NIFI:
                            result = result.to_nifi_result()
                        elif platform == Platform.AIRFLOW:
                            result = result.to_airflow_result()
                        
                        span.set_status(StatusCode.OK)
                        return result
                    else:
                        span.set_status(StatusCode.OK)
                        return result
                    
                except Exception as error:
                    # 오류 정보 기록
                    _record_error(span, error)
                    raise
                    
                finally:
                    # 종료 시간 기록
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    span.set_attribute("etl.duration", duration)
                    span.set_attribute("etl.end_time", end_time.isoformat())
        
        return wrapper
    return decorator


# 플랫폼별 편의 데코레이터
def traced_nifi(group_name: str = "ETL NIFI"):
    """
    NiFi 전용 트레이싱 데코레이터
    
    Arguments:
    ----------
    group_name : str
        작업이 속한 그룹 이름
    force_flush_on_error : bool
        에러 발생 시 강제로 span 전송할지 여부
    """
    return traced(group_name=group_name, platform=Platform.NIFI)


def traced_airflow(task_group: str = "ETL Airflow"):
    """
    Airflow 전용 트레이싱 데코레이터
    
    Arguments:
    ----------
    task_group : str
        작업이 속한 그룹 이름
    force_flush_on_error : bool
        에러 발생 시 강제로 span 전송할지 여부
    """
    return traced(group_name=task_group, platform=Platform.AIRFLOW)