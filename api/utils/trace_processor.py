from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Literal
import json
from dataclasses import dataclass

@dataclass
class ProcessExecutionData:
    """ETL 프로세스 실행 데이터 모델"""
    host_name: str
    platform_type: str
    group_name: str
    process_name: str
    script_name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    success: Literal["SUCCESS", "FAILED"] = "SUCCESS"
    
    # 선택적 필드들
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    source_system_type: Optional[str] = None
    source_system_name: Optional[str] = None
    source_endpoint: Optional[str] = None
    source_object_name: Optional[str] = None
    source_count: Optional[int] = None
    target_system_type: Optional[str] = None
    target_system_name: Optional[str] = None
    target_endpoint: Optional[str] = None
    target_object_name: Optional[str] = None
    target_count: Optional[int] = None
    auto_json: Optional[str] = None

def span_to_execution_data(
        span: Dict[str, Any],
        resource_attributes: Dict[str, str],
        auto_instrumentation_spans: Dict[str, List[Dict[str, Any]]]
    ) -> Optional[ProcessExecutionData]:
    """스팬 데이터를 ProcessExecution 모델 포맷으로 변환"""
    # 필수 필드 확인
    if not all(key in span for key in ["name", "startTimeUnixNano", "endTimeUnixNano"]):
        return None
        
    # 속성 추출 
    attributes = {}
    for attr in span.get("attributes", []):
        key = attr.get("key")
        value_obj = attr.get("value", {})
        
        # 타입에 따라 값 추출
        if "stringValue" in value_obj:
            value = value_obj["stringValue"]
        elif "intValue" in value_obj:
            value = int(value_obj["intValue"])
        elif "boolValue" in value_obj:
            value = bool(value_obj["boolValue"])
        elif "doubleValue" in value_obj:
            value = float(value_obj["doubleValue"])
        else:
            continue
            
        attributes[key] = value
    
    # 기본 정보 추출
    host_name = resource_attributes.get("host.name", "unknown")
    
    # ETL 프로세스 속성이 있는지 확인 (수동 계측된 스팬인지)
    if "etl.process_name" not in attributes:
        return None
        
    # 시간 정보 변환
    # 시작, 종료 시간 및 duration 계산
    # 우선 etl.start_time과 etl.end_time (문자열)이 있는지 확인
    start_time_str = next((attr["value"]["stringValue"] for attr in span.get("attributes", [])
                            if attr["key"] == "etl.start_time"), None)
    end_time_str = next((attr["value"]["stringValue"] for attr in span.get("attributes", [])
                          if attr["key"] == "etl.end_time"), None)
    
    if start_time_str and end_time_str:
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)
    else:
        # Fallback: convert UnixNano timestamps
        start_time = datetime.fromtimestamp(int(span.get("startTimeUnixNano")) / 1e9)
        end_time = datetime.fromtimestamp(int(span.get("endTimeUnixNano")) / 1e9)
    
    duration = (end_time - start_time).total_seconds()
    
    # 성공 여부
    success = "SUCCESS"
    status_code = span.get("status", {}).get("code", "STATUS_CODE_OK")
    if status_code != "STATUS_CODE_OK":
        success = "FAILED"
    
    # 플랫폼 유형 판별 (속성 또는 네이밍 기반)
    if "etl.platform" in attributes:
        platform_type = attributes["etl.platform"]
    elif "airflow" in span["name"].lower() or "dag" in attributes.get("etl.group_name", "").lower():
        platform_type = "AirFlow"
    else:
        platform_type = "NiFi"
    
    # 그룹명과 프로세스명 결정
    group_name = attributes.get("etl.group_name", "unknown")
    process_name = attributes.get("etl.process_name", span["name"])
    script_name = attributes.get("etl.script_name", None)

    # 에러 정보
    error_message = attributes.get("etl.error", None)
    error_type = attributes.get("etl.error_type", None)
    
    # 소스 시스템 정보 추출
    source_system_type = attributes.get("etl.source_system_type",None)
    source_system_name = attributes.get("etl.source_system_name",None)
    source_endpoint = attributes.get("etl.source_endpoint",None)
    source_object_name = attributes.get("etl.source_object_name",None)
    source_count = attributes.get("etl.source_count",None)
    
    # 타겟 시스템 정보 추출
    target_system_type = attributes.get("etl.target_system_type",None)
    target_system_name = attributes.get("etl.target_system_name",None)
    target_endpoint = attributes.get("etl.target_endpoint",None)
    target_object_name = attributes.get("etl.target_object_name",None)
    target_count = attributes.get("etl.target_count",None)
    
    # 문자열 count를 정수로 변환
    if isinstance(source_count, str) and source_count.isdigit():
        source_count = int(source_count)
    if isinstance(target_count, str) and target_count.isdigit():
        target_count = int(target_count)
    
    # 자동계측 데이터 추출 (같은 trace ID를 가진 자동계측 스팬들 찾기)
    auto_json = None
    if "traceId" in span:   
        trace_id = span["traceId"]
        if trace_id in auto_instrumentation_spans:
            auto_spans = auto_instrumentation_spans[trace_id]
            # 자동계측 스팬들의 주요 정보를 JSON으로 변환
            auto_spans_data = []
            for auto_span in auto_spans:
                # span_data = {
                #     "span_id": auto_span.get("spanId"),
                #     "name": auto_span.get("name"),
                #     "kind": auto_span.get("kind", "INTERNAL")
                # }
                
                # 속성 추가
                span_attributes = {}
                for attr in auto_span.get("attributes", []):
                    key = attr.get("key")
                    value_obj = attr.get("value", {})
                    if "stringValue" in value_obj:
                        span_attributes[key] = value_obj["stringValue"]
                    elif "intValue" in value_obj:
                        span_attributes[key] = int(value_obj["intValue"])
                    elif "boolValue" in value_obj:
                        span_attributes[key] = bool(value_obj["boolValue"])
                    elif "doubleValue" in value_obj:
                        span_attributes[key] = float(value_obj["doubleValue"])
                
                auto_spans_data.append(span_attributes)
            
            if auto_spans_data:
                auto_json = json.dumps(auto_spans_data)

    # 결과 데이터
    return ProcessExecutionData(
        host_name=host_name,
        platform_type=platform_type,
        group_name=group_name,
        process_name=process_name,
        script_name=script_name,
        success=success,
        start_time=start_time,
        end_time=end_time,
        duration_seconds=duration,
        error_message=error_message,
        error_type=error_type,
        source_system_type=source_system_type,
        source_system_name=source_system_name,
        source_endpoint=source_endpoint,
        source_object_name=source_object_name,
        source_count=source_count,
        target_system_type=target_system_type,
        target_system_name=target_system_name,
        target_endpoint=target_endpoint,
        target_object_name=target_object_name,
        target_count=target_count,
        auto_json=auto_json
    )


def extract_process_executions(trace_data: Dict[str, Any]) -> List[ProcessExecutionData]:
    """OpenTelemetry 트레이스 데이터에서 프로세스 실행 정보 추출"""
    executions = []
    
    # 자동계측 스팬을 trace_id별로 먼저 수집
    auto_instrumentation_spans = {}
    
    # 먼저 전체 trace 데이터에서 자동계측 스팬 찾기
    for resource_span in trace_data.get("resourceSpans", []):
        # 리소스 속성 추출
        resource_attributes = {}
        for attr in resource_span.get("resource", {}).get("attributes", []):
            key = attr.get("key")
            value_obj = attr.get("value", {})
            if "stringValue" in value_obj:
                resource_attributes[key] = value_obj["stringValue"]
    
        for scope_span in resource_span.get("scopeSpans", []):
            for span in scope_span.get("spans", []):
                # 수동계측 스팬 확인 (ETL 속성이 없는 스팬은 자동계측으로 간주)
                is_manual_instrumentation = False
                for attr in span.get("attributes", []):
                    if attr.get("key", "").startswith("etl."):
                        is_manual_instrumentation = True
                        break
                
                # 자동계측 스팬이면 trace_id별로 저장
                if not is_manual_instrumentation and "traceId" in span:
                    trace_id = span["traceId"]
                    if trace_id not in auto_instrumentation_spans:
                        auto_instrumentation_spans[trace_id] = []
                    auto_instrumentation_spans[trace_id].append(span)
    
    # 이제 수동계측 스팬을 처리하며 자동계측 데이터와 연결
    for resource_span in trace_data.get("resourceSpans", []):
        # 리소스 속성 추출
        resource_attributes = {}
        for attr in resource_span.get("resource", {}).get("attributes", []):
            key = attr.get("key")
            value_obj = attr.get("value", {})
            if "stringValue" in value_obj:
                resource_attributes[key] = value_obj["stringValue"]
        
        # 각 스코프의 스팬 처리
        for scope_span in resource_span.get("scopeSpans", []):
            for span in scope_span.get("spans", []):
                execution_data = span_to_execution_data(span, resource_attributes, auto_instrumentation_spans)
                if execution_data:
                    executions.append(execution_data)
    
    return executions

if __name__ == "__main__":
    with open("/home/younpark/OtelMon/api/utils/test.json", "r") as f:
        trace_data = json.load(f)
    executions = extract_process_executions(trace_data)
    print(executions)