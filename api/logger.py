import logging
import sys
from pathlib import Path
import json
from logging.handlers import RotatingFileHandler
import os

# 환경 변수에서 로그 디렉토리 가져오기, 기본값은 상대 경로
LOG_DIR = Path(os.environ.get("LOG_DIR", "./logs"))
LOG_DIR.mkdir(exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    """지정된 이름으로 로거를 생성합니다."""
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 설정되어 있으면 반환
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.DEBUG)  # 로거 레벨 설정
    
    # 로그 포맷 (이미지에 표시된 형식)
    log_format = '[%(asctime)s] %(process)d, "%(filename)s", %(lineno)d, %(funcName)s : %(message)s'
    date_format = '%Y/%m/%d %H:%M:%S'
    formatter = logging.Formatter(log_format, datefmt=date_format)
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 추가
    log_file = LOG_DIR / f"{name}.log"
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10000000,  # 10MB
        backupCount=9
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

# 기본 앱 로거
app_logger = get_logger("app")
