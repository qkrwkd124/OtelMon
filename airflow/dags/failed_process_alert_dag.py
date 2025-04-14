"""
실패 프로세스 알람 DAG.

DB에서 실패한 프로세스를 폴링하여 이메일로 알람을 보내는 DAG입니다.
"""
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

import pandas as pd

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago
from airflow.operators.email import EmailOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook

# 플러그인 임포트
from trace_log import traced_task, Result

# SQL 파일 경로 설정
SQL_DIR = Path(__file__).parent / 'sql'

# 상수 정의
CONN_ID = 'log_db'  # DB 연결 ID
EMAIL_RECIPIENT = ["younpark@mobigen.com"] # 이메일 수신자
SCHEDULE_INTERVAL = '@once'  # 30분마다 실행


def read_sql_file(filename: str) -> str:
    """SQL 파일을 읽어 내용을 반환합니다.
    
    Args:
        filename: SQL 파일명
        
    Returns:
        SQL 쿼리 문자열
    """
    sql_path = SQL_DIR / filename
    return sql_path.read_text(encoding='utf-8')


# 기본 인수 정의
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    # 'retries': 1,
    # 'retry_delay': timedelta(minutes=5),
}


@dag(
    dag_id='failed_process_alert',
    default_args=default_args,
    description='DB에서 실패한 프로세스를 폴링하여 이메일 알람 전송',
    schedule_interval=SCHEDULE_INTERVAL,
    start_date=days_ago(1),
    tags=['alert', 'email', 'monitoring'],
)
def failed_process_alert():
    """DB에서 실패한 프로세스를 폴링하여 이메일 알람 전송하는 DAG."""
    
    @task(task_id='create_alert_history_table')
    @traced_task(task_group="failed_process_alert")
    def create_alert_history_table() -> Dict[str, Any]:
        """알람 이력 테이블이 없으면 생성합니다."""
        hook = MySqlHook(mysql_conn_id=CONN_ID)
        
        create_table_query = read_sql_file('create_alert_history.sql')
        hook.run(create_table_query)
        
        return {"hook_conn_id": CONN_ID}
    
    @task(task_id='get_new_failed_processes')
    @traced_task(task_group="failed_process_alert")
    def get_new_failed_processes(context: Dict[str, Any]) -> Dict[str, Any]:
        """DB에서 아직 알람을 보내지 않은 실패한 프로세스를 조회합니다."""
        hook = MySqlHook(mysql_conn_id=CONN_ID)
        
        query = read_sql_file('get_new_failed_processes.sql')
        df = hook.get_pandas_df(query)

        # timestamp 컬럼을 문자열로 변환
        if not df.empty:
            for col in ['start_time', 'end_time']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # 기타 복잡한 데이터 타입도 문자열로 변환하여 XCOM 직렬화 문제 방지
            for col in df.columns:
                if df[col].dtype.name not in ['object', 'str', 'int64', 'float64', 'bool']:
                    df[col] = df[col].astype(str)
        
        process_count = len(df)
        print(f"새로운 실패 프로세스 발견: {process_count}개")
        
        result = Result(
            result={"failed_processes": df.to_dict(orient='records')},
            trace_metric={},
            process_count=process_count
        )
        
        return result.result
    
    @task(task_id='generate_html_report')
    @traced_task(task_group="failed_process_alert")
    def generate_html_report(context: Dict[str, Any]) -> Dict[str, Any]:
        """HTML 테이블 형식의 리포트를 생성합니다."""
        failed_processes = context.get("failed_processes", [])
        
        if not failed_processes:
            return {
                "html_content": "", 
                "has_failures": False, 
                "failed_processes": []
            }
        
        # 데이터프레임 생성 및 형식 지정
        df = pd.DataFrame(failed_processes)
        
        # # 타임스탬프 열 서식 지정
        # for col in ['start_time', 'end_time']:
        #     if col in df.columns:
        #         df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # HTML 콘텐츠 생성
        html_content = _create_html_content(df, len(failed_processes))
        
        result = Result(
            result={
                "html_content": html_content, 
                "has_failures": True, 
                "failed_processes": failed_processes
            },
            trace_metric={},
            process_count=len(failed_processes)
        )
        
        return result.result
    
    @task(task_id='send_email_task')
    @traced_task(task_group="failed_process_alert")
    def prepare_and_send_email(context: Dict[str, Any]) -> Dict[str, Any]:
        """이메일 알림을 준비하고 전송합니다."""
        html_content = context.get("html_content", "")
        has_failures = context.get("has_failures", False)
        failed_processes = context.get("failed_processes", [])
        
        if not has_failures:
            print("새로운 실패 프로세스가 없습니다. 이메일을 전송하지 않습니다.")
            return {"email_sent": False}
        
        # 이메일 전송
        _send_email_alert(html_content)
        
        # 알람 이력 저장
        _save_alert_history(failed_processes)
        
        result = Result(
            result={"email_sent": True},
            trace_metric={},
            process_count=1
        )
        
        return result.result
    
    def _create_html_content(df: pd.DataFrame, failure_count: int) -> str:
        """HTML 테이블 형식의 콘텐츠를 생성합니다.
        
        Args:
            df: 실패 프로세스 데이터프레임
            failure_count: 실패 건수
            
        Returns:
            HTML 형식의 문자열
        """
        # HTML 스타일 지정
        html_style = """
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h2 {
                color: #2c3e50;
                margin: 0;
                font-size: 24px;
            }
            .info {
                color: #666;
                margin: 10px 0;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                border-radius: 8px;
                overflow: hidden;
            }
            th {
                background-color: #3498db;
                color: white;
                font-weight: 600;
                padding: 12px;
                text-align: left;
                font-size: 14px;
            }
            td {
                padding: 12px;
                border-bottom: 1px solid #eee;
                font-size: 14px;
            }
            tr:nth-child(even) {
                background-color: #f8f9fa;
            }
            tr:hover {
                background-color: #f1f1f1;
            }
            .error-msg {
                color: #e74c3c;
                font-weight: 500;
                background-color: #fde8e8;
                padding: 4px 8px;
                border-radius: 4px;
            }
            .platform {
                font-weight: 600;
                color: #2c3e50;
            }
            .group {
                color: #7f8c8d;
            }
            .duration {
                font-family: monospace;
                color: #3498db;
            }
            @media (max-width: 768px) {
                table {
                    display: block;
                    overflow-x: auto;
                }
                th, td {
                    min-width: 120px;
                }
            }
        </style>
        """
        
        # 현재 시간
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # HTML 헤더
        html_header = f"""
        <div class="header">
            <h2>프로세스 실패 알람 리포트</h2>
            <div class="info">
                <p>실행 시간: {now}</p>
                <p>발견된 새로운 실패 건수: <strong>{failure_count}</strong></p>
            </div>
        </div>
        """
        
        # 데이터프레임을 HTML 테이블로 변환
        html_table = df.to_html(
            index=False, 
            classes='table', 
            escape=False,
            formatters={
                'error_message': lambda x: f'<span class="error-msg">{x}</span>' if x else '',
                'platform_type': lambda x: f'<span class="platform">{x}</span>',
                'group_name': lambda x: f'<span class="group">{x}</span>',
                'duration_seconds': lambda x: f'<span class="duration">{x:.2f}s</span>'
            }
        )
        
        # 최종 HTML 콘텐츠
        return f"{html_style}{html_header}{html_table}"
    
    def _send_email_alert(html_content: str) -> None:
        """이메일 알람을 전송합니다.
        
        Args:
            html_content: 이메일 본문 HTML
        """
        email_subject = f"[알람] 프로세스 실패 알림 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        email_task = EmailOperator(
            task_id='send_email',
            to=EMAIL_RECIPIENT,
            subject=email_subject,
            html_content=html_content,
            dag=None
        )
        
        email_task.execute(context={})
        print(f"이메일 알람이 {EMAIL_RECIPIENT}로 전송되었습니다.")
    
    def _save_alert_history(failed_processes: List[Dict[str, Any]]) -> None:
        """알람 발송 이력을 DB에 저장합니다. 각 프로세스 실행 ID만 저장합니다.
        
        Args:
            failed_processes: 실패 프로세스 목록
        """
        if not failed_processes:
            return
            
        hook = MySqlHook(mysql_conn_id=CONN_ID)
        
        for process in failed_processes:
            # process_execution_id만 사용하여 이력 저장
            insert_query = """
            INSERT IGNORE INTO alert_history 
                (process_execution_id, platform_type, group_name, process_name, end_time)
            VALUES 
                (%s, %s, %s, %s, %s)
            """
            
            hook.run(
                insert_query, 
                parameters=(
                    process['id'],  # ProcessExecution 테이블의 id
                    process['platform_type'],
                    process['group_name'],
                    process['process_name'],
                    process['end_time']
                )
            )
        
        print(f"알람 이력 {len(failed_processes)}개가 DB에 저장되었습니다.")
    
    # 워크플로우 정의
    table_info = create_alert_history_table()
    failed_data = get_new_failed_processes(table_info)
    html_report = generate_html_report(failed_data)
    send_email_result = prepare_and_send_email(html_report)


# DAG 인스턴스 생성
failed_process_alert_dag = failed_process_alert()