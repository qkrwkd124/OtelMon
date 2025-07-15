from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from typing import TypeVar, Type, List, Dict, Any, Generic

from logger import get_logger
from models.telemetry import Base, ProcessExecution
from utils.trace_processor import ProcessExecutionData

logger = get_logger(__name__)

# SQLAlchemy 모델 타입 변수
T = TypeVar('T')

class BaseDBService:
    """기본 데이터베이스 서비스"""
    
    def __init__(self, config):
        self.database_url = config.DATABASE_URL
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        logger.info(f"데이터베이스 서비스 초기화: {self.database_url}")

    @contextmanager
    def get_session(self):
        """세션 컨텍스트 매니저"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()


class ProcessExecutionService(BaseDBService):
    """프로세스 실행 정보 관련 서비스"""
    
    def __init__(self, config):
        super().__init__(config)
        # 테이블 생성
        Base.metadata.create_all(self.engine)
    
    async def save_execution(self, execution_data: ProcessExecutionData) -> int:
        """프로세스 실행 정보를 데이터베이스에 저장"""
        try:
            with self.get_session() as session:
                execution = ProcessExecution(
                    host_name=execution_data.host_name,
                    platform_type=execution_data.platform_type,
                    group_name=execution_data.group_name,
                    process_name=execution_data.process_name,
                    script_name=execution_data.script_name,
                    success=execution_data.success,
                    error_message=execution_data.error_message,
                    error_type=execution_data.error_type,
                    start_time=execution_data.start_time,
                    end_time=execution_data.end_time,
                    duration_seconds=execution_data.duration_seconds,
                    
                    # 소스 시스템 정보
                    source_system_type=execution_data.source_system_type,
                    source_system_name=execution_data.source_system_name,
                    source_endpoint=execution_data.source_endpoint,
                    source_object_name=execution_data.source_object_name,
                    source_count=execution_data.source_count,
                    # 대상 시스템 정보
                    target_system_type=execution_data.target_system_type,
                    target_system_name=execution_data.target_system_name,
                    target_endpoint=execution_data.target_endpoint,
                    target_object_name=execution_data.target_object_name,
                    target_count=execution_data.target_count,

                    #자동계측 데이터
                    auto_json=execution_data.auto_json
                )
                
                session.add(execution)
                session.flush()
                
                logger.info(f"실행 정보 저장 성공: {execution}")
                return execution.id
                
        except SQLAlchemyError as e:
            logger.error(f"데이터베이스 저장 실패: {str(e)}", exc_info=True)
            raise
    
    async def get_executions(self, limit: int = 100) -> List[ProcessExecution]:
        """최근 실행 정보 조회"""
        try:
            with self.get_session() as session:
                executions = session.query(ProcessExecution)\
                    .order_by(ProcessExecution.start_time.desc())\
                    .limit(limit)\
                    .all()
                return executions
        except SQLAlchemyError as e:
            logger.error(f"실행 정보 조회 실패: {str(e)}", exc_info=True)
            raise
    
    async def get_failed_executions(self, days: int = 1) -> List[ProcessExecution]:
        """최근 N일 내 실패한 실행 정보 조회"""
        from datetime import datetime, timedelta
        
        try:
            with self.get_session() as session:
                since = datetime.now() - timedelta(days=days)
                
                executions = session.query(ProcessExecution)\
                    .filter(ProcessExecution.success == False)\
                    .filter(ProcessExecution.start_time >= since)\
                    .order_by(ProcessExecution.start_time.desc())\
                    .all()
                return executions
        except SQLAlchemyError as e:
            logger.error(f"실패 정보 조회 실패: {str(e)}", exc_info=True)
            raise


# 새로운 모델에 대한 서비스 클래스 예시
# class AlertService(BaseDBService):
#     """알림 관련 서비스"""
#     
#     def __init__(self, config):
#         super().__init__(config)
#     
#     async def save_alert(self, alert_data: dict) -> int:
#         """알림 정보 저장"""
#         with self.get_session() as session:
#             # 알림 저장 로직
#             pass 