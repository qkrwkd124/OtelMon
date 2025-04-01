import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Literal, Optional, Callable, Any

import settings

# Logging Configure
PYTHON_LOGGING_PATH = settings.PYTHON_LOGGING_PATH
PYTHON_LOGGING_FORMAT = settings.PYTHON_LOGGING_FORMAT
PYTHON_LOGGING_MAX_SIZE = settings.PYTHON_LOGGING_MAX_SIZE
PYTHON_LOGGING_BACKUP_COUNT = settings.PYTHON_LOGGING_BACKUP_COUNT


def log(mode:Literal["development", "production", "debug"], log_name:Optional[str]=None) -> Callable:
    """
    로그 설정하는 데코레이터

    Envs
    ----
    PYTHON_LOGGING_PATH: str
        로깅 저장 디렉토리
    PYTHON_LOGGING_FORMAT: str
        로깅 포맷
    PYTHON_LOGGING_MAX_SIZE:
    PYTHON_LOGGING_BACKUP_COUNT
    
    Parameters
    ----------
    mode: Literal["development", "production", "debug"]
        모드 설정
    log_name: Optional[str], None
        작성할 로그의 파일 이름. production mode 일때 사용
    
    Example
    -------
    log.PYTHON_LOGGING_FORMAT = "%(message)s"
    @log(mode=development)
    def add(a, b):
        logging.info("Result: %d" % a + b) # Result: 3
    add(1, 2)


    """
    def decorator(func: Callable[..., Any]) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger()
    
            # 모드에 따라 Level 처리
            if mode in ["debug", "development"]:
                logger.setLevel(logging.DEBUG)
            elif mode == "production":
                logger.setLevel(logging.INFO)

            # 모드에 따라 Handler 처리
            if mode == "production":
                if log_name is None:
                    raise ValueError("Cannot make log file")
                # 배포 모드는 파일로 로깅 처리
                handler = RotatingFileHandler(
                    os.path.join(PYTHON_LOGGING_PATH, f'{log_name}.log'),
                    maxBytes=PYTHON_LOGGING_MAX_SIZE,
                    backupCount=PYTHON_LOGGING_BACKUP_COUNT
                )
            else:
                # 그 외 모드는 표준입출력으로 로깅 처리
                handler = logging.StreamHandler()

            # 로그 포맷 설정
            formatter = logging.Formatter(PYTHON_LOGGING_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
            handler.setFormatter(formatter)

            # Handler 추가
            logger.addHandler(handler)

            # 프로세스
            result = func(*args, **kwargs)

            # Handler 삭제
            logger.removeHandler(handler)

            return result
        return wrapper
    return decorator