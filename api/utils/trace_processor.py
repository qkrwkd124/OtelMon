from datetime import datetime
from typing import Dict, Any, Optional, List
import json

def span_to_execution_data(span: Dict[str, Any], resource_attributes: Dict[str, str]) -> Optional[Dict[str, Any]]:
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
    success = True
    status_code = span.get("status", {}).get("code", "STATUS_CODE_OK")
    if status_code != "STATUS_CODE_OK":
        success = False
    
    # 플랫폼 유형 판별 (속성 또는 네이밍 기반)
    if "etl.platform" in attributes:
        platform_type = attributes["etl.platform"]
    elif "airflow" in span["name"].lower() or "dag" in attributes.get("etl.group_name", "").lower():
        platform_type = "airflow"
    else:
        platform_type = "nifi"
    
    # 그룹명과 프로세스명 결정
    group_name = attributes.get("etl.group_name", "unknown")
    process_name = attributes.get("etl.process_name", span["name"])
    
    # 에러 정보
    error_message = attributes.get("etl.error", None)
    error_type = attributes.get("etl.error_type", None)
    
    # trace와 span ID
    # trace_id = decode_trace_id(span.get("traceId", ""))
    # span_id = decode_trace_id(span.get("spanId", ""))
    
    # 결과 데이터
    return {
        "host_name": host_name,
        "platform_type": platform_type,
        "group_name": group_name,
        "process_name": process_name,
        "success": success,
        # "attributes": attributes,
        "error_message": error_message,
        "error_type": error_type,
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": duration,
        # "trace_id": trace_id,
        # "span_id": span_id
    }

def extract_process_executions(trace_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """OpenTelemetry 트레이스 데이터에서 프로세스 실행 정보 추출"""
    executions = []
    
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
                execution_data = span_to_execution_data(span, resource_attributes)
                if execution_data:
                    executions.append(execution_data)
    
    return executions


if __name__ == "__main__":
    with open("/home/younpark/OtelMon/api/utils/test.json", "r") as f:
        trace_data = json.load(f)
    executions = extract_process_executions(trace_data)
    print(executions)