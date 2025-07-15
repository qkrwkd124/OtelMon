from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ProcessExecution(Base):
    __tablename__ = "process_executions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    host_name = Column(String(100), nullable=False, index=True)
    platform_type = Column(String(20), nullable=False, index=True)  # 'airflow' 또는 'nifi'
    group_name = Column(String(200), nullable=False, index=True)    # dag_id 또는 process_group
    process_name = Column(String(200), nullable=False, index=True)  # task_id 또는 processor_name
    script_name = Column(String(200), nullable=False, index=True)  # script_name
    success = Column(Boolean, nullable=False, index=True)
    # attributes = Column(JSON, nullable=True)                        # 추가 속성 정보
    error_message = Column(Text, nullable=True)
    error_type = Column(String(100), nullable=True)

    # 소스 시스템 정보
    source_system_type = Column(String(50), comment='출처시스템타입')
    source_system_name = Column(String(100), comment='출처시스템명')
    source_endpoint = Column(String(500), comment='출처종료포인트명명')
    source_object_name = Column(String(200), comment='출처시스템객체명')
    source_count = Column(Integer, comment='출처시스템처리건수')

    # 대상 시스템 정보
    target_system_type = Column(String(50), comment='대상시스템타입')
    target_system_name = Column(String(100), comment='대상시스템명')
    target_endpoint = Column(String(500), comment='대상종료포인트명명')
    target_object_name = Column(String(200), comment='대상시스템객체명')
    target_count = Column(Integer, comment='대상시스템처리건수')
    
    # 자동계측 속성
    auto_json = Column(String(4000), comment='자동계측속성')

    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    # trace_id = Column(String(50), nullable=True, index=True)
    # span_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<ProcessExecution(id={self.id}, platform={self.platform_type}, group={self.group_name}, process={self.process_name}, success={self.success})>"
