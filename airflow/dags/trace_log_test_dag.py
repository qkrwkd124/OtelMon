from datetime import datetime, timedelta
import random
import time
import requests
from typing import Dict, Any

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

# 플러그인 임포트
from trace_log import traced_airflow, Result
from system_info import SimpleSystemInfo

# 기본 인수 정의
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    # 'retries': 1,
    # 'retry_delay': timedelta(minutes=5),
}

@dag(
    dag_id='trace_log_test_taskflow',
    default_args=default_args,
    description='OpenTelemetry 트레이싱 테스트 DAG (TaskFlow API)',
    # schedule_interval=timedelta(days=1),
    schedule_interval='@once',
    start_date=days_ago(1),
    tags=['test', 'otel', 'trace', 'taskflow'],
)
def trace_log_test_taskflow():
    """TaskFlow API를 사용한 OpenTelemetry 트레이싱 테스트 DAG"""
    
    # 태스크 정의 - 데이터 생성
    @task(task_id='generate_data')
    @traced_airflow(task_group="trace_log_test_taskflow")
    def generate_data() -> Dict[str, Any]:
        """테스트용 데이터를 생성하는 함수"""
        # 작업 시뮬레이션
        time.sleep(random.uniform(1, 3))
        
        # 생성할 데이터 항목 수
        num_items = random.randint(10, 50)
        
        # 결과 데이터 생성
        data = [{"id": i, "value": random.randint(1, 100)} for i in range(num_items)]
        
        # 메트릭 정보
        metrics = {
            "data.count": num_items,
            "data.generation_time": datetime.now().isoformat()
        }
        
        result = Result(
            result={"data": data},
            process_count=num_items
        )
        
        # TaskFlow API에서는 딕셔너리를 반환해야 합니다
        return result
    
    # 태스크 정의 - 데이터 변환
    @task(task_id='transform_data')
    @traced_airflow(task_group="trace_log_test_taskflow")
    def transform_data(data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """데이터를 변환하는 함수"""
        # 작업 시뮬레이션
        time.sleep(random.uniform(2, 4))
        
        # 데이터 변환 로직
        data = data_dict["data"]
        transformed_data = [{"id": item["id"], "transformed_value": item["value"] * 2} for item in data]
        
        # 가끔 오류 발생 시뮬레이션 (10% 확률로 오류 발생)
        if random.random() < 0.5:
            raise Exception("랜덤 변환 오류 발생")
        
        # 메트릭 정보
        metrics = {
            "data.transformed_count": len(transformed_data),
            "data.transformation_time": datetime.now().isoformat()
        }
        
        result = Result(
            result={"transformed_data": transformed_data},
            process_count=len(transformed_data)
        )
        
        return result
    
    # 태스크 정의 - 외부 API 호출
    @task(task_id='call_external_api')
    @traced_airflow(task_group="trace_log_test_taskflow")
    def call_external_api() -> Dict[str, Any]:
        """외부 API를 호출하는 함수 (requests 라이브러리 자동 계측 테스트)"""
        # 작업 시뮬레이션
        time.sleep(random.uniform(1, 2))
        
        # 외부 API 호출 (실제로는 requestbin이나 테스트 엔드포인트로 대체)
        response = requests.get("https://httpbin.org/get")
        response_data = response.json()
        
        # 메트릭 정보
        metrics = {
            "api.status_code": response.status_code,
            "api.response_time": response.elapsed.total_seconds()
        }
        
        result = Result(
            result={"api_response": response_data},
            process_count=1,
            source_info=SimpleSystemInfo.create_api(
                api_base_url="https://httpbin.org",
                api_endpoint="/get",
                response_count=1
            )
        )
        
        return result
    
    # 태스크 정의 - 결과 요약
    @task(task_id='generate_report')
    @traced_airflow(task_group="trace_log_test_taskflow")
    def generate_report(transform_data_dict: Dict[str, Any], api_data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """결과 보고서를 생성하는 함수"""
        # 작업 시뮬레이션
        time.sleep(random.uniform(1, 3))
        
        # 보고서 데이터 생성
        report = {
            "timestamp": datetime.now().isoformat(),
            "transform_count": len(transform_data_dict["transformed_data"]),
            "api_status": api_data_dict["api_response"]["url"]
        }
        
        # 메트릭 정보
        metrics = {
            "report.generation_time": datetime.now().isoformat(),
            "report.item_count": len(transform_data_dict["transformed_data"])
        }
        
        print(f"보고서 생성 완료: {report}")
        
        result = Result(
            result={"report": report},
            process_count=1
        )
        
        return result
    
    # TaskFlow API 워크플로우 구성
    data = generate_data()
    transformed_data = transform_data(data)
    api_data = call_external_api()
    generate_report(transformed_data, api_data)

# DAG 인스턴스 생성
trace_log_dag = trace_log_test_taskflow()