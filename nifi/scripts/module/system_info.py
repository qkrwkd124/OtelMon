from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Literal, Union
from pathlib import Path
from enum import Enum


# 타입 별칭으로 허용되는 값들을 명시
DatabaseType = Literal["mysql", "postgresql", "oracle", "mssql", "mongodb", "redis", "mariadb", "sqlite"]
FileType = Literal["csv", "excel", "json", "xml", "txt", "parquet", "avro", "orc"]
ApiType = Literal["rest_api", "soap_api", "graphql", "websocket"]
CloudProvider = Literal["aws_s3", "azure_blob", "gcs", "minio"]
QueueType = Literal["apache_kafka", "rabbitmq", "activemq", "redis_queue"]


class SystemType(Enum):
    """시스템 타입 정의"""
    DATABASE = "database"
    FILE = "file"
    API = "api"
    HTTP = "http"
    FTP = "ftp"
    SFTP = "sftp"
    S3 = "s3"
    KAFKA = "kafka"
    QUEUE = "queue"
    CACHE = "cache"
    EMAIL = "email"
    
    @classmethod
    def get_suggestions(cls) -> List[str]:
        """사용 가능한 시스템 타입 목록 반환"""
        return [item.value for item in cls]


@dataclass
class SimpleSystemInfo:
    """
    시스템 정보를 정의하는 클래스
    
    ETL 프로세스에서 사용되는 소스 또는 타겟 시스템의 정보를 저장합니다.
    """
    
    system_type: str
    system_name: str
    endpoint: Optional[str] = None
    object_name: Optional[str] = None
    count: Optional[int] = None
    
    def __post_init__(self):
        """초기화 후 간단한 검증"""
        if self.system_type not in SystemType.get_suggestions():
            suggested = SystemType.get_suggestions()
            print(f"⚠️ 권장 system_type: {', '.join(suggested)}")
    
    @classmethod
    def create_database(
        cls,
        database_type: DatabaseType,
        host_and_port: str,
        table_name: Optional[str] = None,
        record_count: Optional[int] = None
    ) -> 'SimpleSystemInfo':
        """
        데이터베이스 시스템 정보를 생성합니다.
        
        Args:
            database_type: 데이터베이스 종류
                - "mysql": MySQL 데이터베이스
                - "postgresql": PostgreSQL 데이터베이스  
                - "oracle": Oracle 데이터베이스
                - "mssql": Microsoft SQL Server
                - "mongodb": MongoDB (NoSQL)
                - "redis": Redis (인메모리 DB)
                - "mariadb": MariaDB
                - "sqlite": SQLite
                
            host_and_port: 데이터베이스 연결 주소
                예시: "localhost:3306", "db.example.com:5432", "127.0.0.1:1433"
                
            table_name: 테이블/컬렉션 이름 (선택사항)
                예시: "users", "products", "orders", "user_activity"
                
            record_count: 처리된 레코드 수 (선택사항)
                예시: 1000, 50000, 250000
        
        Returns:
            SimpleSystemInfo: 데이터베이스 시스템 정보 객체
            
        Examples:
            >>> # MySQL 사용자 테이블
            >>> db_info = SimpleSystemInfo.create_database(
            ...     database_type="mysql",
            ...     host_and_port="localhost:3306", 
            ...     table_name="users",
            ...     record_count=1000
            ... )
            
            >>> # PostgreSQL 주문 테이블  
            >>> db_info = SimpleSystemInfo.create_database(
            ...     database_type="postgresql",
            ...     host_and_port="postgres.company.com:5432",
            ...     table_name="orders"
            ... )
        """
        return cls(
            system_type=SystemType.DATABASE.value,
            system_name=database_type,
            endpoint=host_and_port,
            object_name=table_name,
            count=record_count
        )
    
    @classmethod
    def create_api(
        cls,
        api_base_url: str,
        api_endpoint: Optional[str] = None,
        response_count: Optional[int] = None,
        api_type: ApiType = "rest_api"
    ) -> 'SimpleSystemInfo':
        """
        API 시스템 정보를 생성합니다.
        
        Args:
            api_base_url: API 기본 URL (프로토콜 포함)
                예시: "https://api.example.com", "http://localhost:8080", "https://jsonplaceholder.typicode.com"
                
            api_endpoint: 구체적인 API 엔드포인트 경로 (선택사항)
                예시: "/api/v1/users", "/users", "/getData", "getUserList"
                
            response_count: API 응답으로 받은 레코드 수 (선택사항)
                예시: 100, 500, 1000
                
            api_type: API 종류
                - "rest_api": REST API (기본값)
                - "soap_api": SOAP API
                - "graphql": GraphQL API
                - "websocket": WebSocket API
        
        Returns:
            SimpleSystemInfo: API 시스템 정보 객체
            
        Examples:
            >>> # 공공데이터 API
            >>> api_info = SimpleSystemInfo.create_api(
            ...     api_base_url="http://apis.data.go.kr/1262000/service",
            ...     api_endpoint="/getUserList",
            ...     response_count=50
            ... )
            
            >>> # 내부 REST API
            >>> api_info = SimpleSystemInfo.create_api(
            ...     api_base_url="https://internal-api.company.com",
            ...     api_endpoint="/api/v2/employees"
            ... )
        """
        return cls(
            system_type=SystemType.HTTP.value,
            system_name=api_type,
            endpoint=api_base_url,
            object_name=api_endpoint,
            count=response_count
        )
    
    @classmethod
    def create_file(
        cls,
        file_full_path: str,
        file_format: FileType = "csv",
        row_count: Optional[int] = None
    ) -> 'SimpleSystemInfo':
        """
        파일 시스템 정보를 생성합니다.
        
        Args:
            file_full_path: 파일의 전체 경로
                예시: "/data/input/users.csv", "C:\\data\\output\\report.xlsx", "./temp/data.json"
                
            file_format: 파일 형식
                - "csv": CSV 파일 (기본값)
                - "excel": Excel 파일 (.xlsx, .xls)
                - "json": JSON 파일
                - "xml": XML 파일
                - "txt": 텍스트 파일
                - "parquet": Parquet 파일
                - "avro": Avro 파일
                - "orc": ORC 파일
                
            row_count: 파일의 레코드 수 (선택사항)
                예시: 1000, 50000, 250000
        
        Returns:
            SimpleSystemInfo: 파일 시스템 정보 객체
            
        Examples:
            >>> # CSV 파일 처리
            >>> file_info = SimpleSystemInfo.create_file(
            ...     file_full_path="/data/input/users.csv",
            ...     file_format="csv",
            ...     row_count=2000
            ... )
            
            >>> # Excel 파일 처리
            >>> file_info = SimpleSystemInfo.create_file(
            ...     file_full_path="C:\\reports\\monthly_report.xlsx",
            ...     file_format="excel"
            ... )
        """
        path = Path(file_full_path)
        return cls(
            system_type=SystemType.FILE.value,
            system_name=file_format,
            endpoint=str(path.parent),
            object_name=path.name,
            count=row_count
        )
    
    @classmethod
    def create_s3(
        cls,
        bucket_name: str,
        object_key_path: str,
        file_count: Optional[int] = None,
        cloud_provider: CloudProvider = "aws_s3"
    ) -> 'SimpleSystemInfo':
        """
        클라우드 스토리지 (S3) 시스템 정보를 생성합니다.
        
        Args:
            bucket_name: S3 버킷 이름
                예시: "my-data-bucket", "company-analytics", "user-uploads"
                
            object_key_path: S3 객체 키 (파일 경로)
                예시: "data/users.json", "reports/daily/2024-01-15.csv", "logs/app.log"
                
            file_count: 처리된 파일/레코드 수 (선택사항)
                예시: 1, 100, 5000
                
            cloud_provider: 클라우드 제공자
                - "aws_s3": Amazon S3 (기본값)
                - "azure_blob": Azure Blob Storage
                - "gcs": Google Cloud Storage
                - "minio": MinIO
        
        Returns:
            SimpleSystemInfo: S3 시스템 정보 객체
            
        Examples:
            >>> # AWS S3 파일 업로드
            >>> s3_info = SimpleSystemInfo.create_s3(
            ...     bucket_name="my-data-bucket",
            ...     object_key_path="processed/users_2024.json",
            ...     file_count=3000
            ... )
            
            >>> # Azure Blob Storage 
            >>> s3_info = SimpleSystemInfo.create_s3(
            ...     bucket_name="analytics-container",
            ...     object_key_path="daily-reports/2024-01-15.csv",
            ...     cloud_provider="azure_blob"
            ... )
        """
        return cls(
            system_type=SystemType.S3.value,
            system_name=cloud_provider,
            endpoint=f"s3://{bucket_name}",
            object_name=object_key_path,
            count=file_count
        )
    
    @classmethod
    def create_kafka(
        cls,
        broker_hosts: str,
        topic_name: str,
        message_count: Optional[int] = None,
        queue_system: QueueType = "apache_kafka"
    ) -> 'SimpleSystemInfo':
        """
        메시지 큐 시스템 정보를 생성합니다.
        
        Args:
            broker_hosts: 메시지 큐 브로커 주소
                예시: "localhost:9092", "kafka1:9092,kafka2:9092", "broker.company.com:9092"
                
            topic_name: 토픽/큐 이름
                예시: "user-events", "order-updates", "system-logs", "notification-queue"
                
            message_count: 처리된 메시지 수 (선택사항)
                예시: 100, 1000, 50000
                
            queue_system: 메시지 큐 시스템 종류
                - "apache_kafka": Apache Kafka (기본값)
                - "rabbitmq": RabbitMQ
                - "activemq": ActiveMQ
                - "redis_queue": Redis Queue
        
        Returns:
            SimpleSystemInfo: 메시지 큐 시스템 정보 객체
            
        Examples:
            >>> # Kafka 토픽에서 데이터 읽기
            >>> kafka_info = SimpleSystemInfo.create_kafka(
            ...     broker_hosts="localhost:9092",
            ...     topic_name="user-activity",
            ...     message_count=5000
            ... )
            
            >>> # RabbitMQ 사용
            >>> kafka_info = SimpleSystemInfo.create_kafka(
            ...     broker_hosts="rabbitmq.company.com:5672",
            ...     topic_name="order-processing",
            ...     queue_system="rabbitmq"
            ... )
        """
        return cls(
            system_type=SystemType.KAFKA.value,
            system_name=queue_system,
            endpoint=broker_hosts,
            object_name=topic_name,
            count=message_count
        )
