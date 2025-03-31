from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # 데이터베이스 설정
    DATABASE_URL: str = "postgresql://username:password@localhost/etlmonitor"
    
    # SMTP 설정
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "younpark0428@gmail.com"
    SMTP_PASSWORD: str = ""
    
    # SMS 설정
    SMS_API_URL: str = "https://api.sms-service.com/send"
    SMS_API_KEY: str = "your-api-key"
    
    # 알림 수신자
    ADMIN_EMAILS: list = ["younpark@mobigen.com"]
    ADMIN_PHONES: list = ["+821012345678"]
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
