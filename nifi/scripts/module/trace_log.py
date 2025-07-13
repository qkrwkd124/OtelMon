import time
import traceback
from datetime import datetime
from dataclasses import dataclass, asdict, field
from functools import wraps
from typing import Dict, Any, Callable, Optional
from pathlib import Path
import inspect
import os

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Span
from opentelemetry.instrumentation.requests import RequestsInstrumentor

@dataclass
class SimpleSystemInfo:
    """시스템 정보"""

    # 필수 필드
    system_type: str  # 'database', 'file', 'api'
    system_name: str  # 'postgresql', 's3', 'rest' 등
    
    # 선택적 공통 필드
    endpoint: Optional[str] = None  # 연결 주소/URL/경로
    object_name: Optional[str] = None  # 테이블/파일/리소스 이름
    count: Optional[int] = None  # 처리된 레코드 수

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

# 전역 변수로 선언
_tracer = None
_instrumented = False

# 설정 상수
SERVICE_NAME = "etl_tracer"
SERVICE_VERSION = "1.0.0"
OTEL_ENDPOINT = "http://otelcol:4317/v1/traces"


def _init_instrumentation():
    """
    자동 계측(Automatic Instrumentation) 설정
    
    이미 초기화되었다면 다시 실행하지 않도록 플래그를 사용
    """
    global _instrumented
    if _instrumented:
        return
    
    RequestsInstrumentor().instrument()
    _instrumented = True


def _init_tracer():
    """
    OpenTelemetry 트레이서 초기화
    
    Returns:
        트레이서 객체
    """
    global _tracer
    if _tracer is not None:
        return _tracer
    
    # 리소스 및 트레이서 설정    
    resource = Resource.create(attributes={
        "service.name": SERVICE_NAME, 
        "service.version": SERVICE_VERSION,
        "host.name": os.getenv('REAL_HOSTNAME', 'cpietl'), 
        "timezone": "Asia/Seoul"
    })
    
    tracer_provider = TracerProvider(resource=resource)
    span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT))
    tracer_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(tracer_provider)
    
    _tracer = trace.get_tracer(__name__)
    return _tracer


def _record_span_attributes(span: Span, result: Result):
    """
    스팬에 결과 속성 기록
    
    Args:
        span: 현재 스팬 객체
        result: 함수 실행 결과
    """
    if isinstance(result, Result):
        span.set_attribute("etl.process_count", result.process_count)
        for key, value in result.trace_attributes.items():
            span.set_attribute(f"{key}", str(value))

def _record_system_info(span: Span,  source: Optional[SimpleSystemInfo]=None, target: Optional[SimpleSystemInfo]=None):
    """
    시스템 정보 기록
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


def traced(group_name="ETL NiFi"):
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
                span.set_attribute("etl.platform", "NiFi")
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
                        nifi_result = result.to_nifi_result()
                        
                        span.set_status(StatusCode.OK)
                        return nifi_result
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
