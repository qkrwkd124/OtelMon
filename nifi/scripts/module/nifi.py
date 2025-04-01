import os
import sys
import io
import json
import uuid
import inspect
import traceback
import logging
from datetime import datetime
from dataclasses import dataclass, asdict, field
from functools import wraps
from contextlib import redirect_stderr, redirect_stdout
from typing import (
    Optional, List, Dict, Any, Literal,
    Callable, Union, Iterable
)
import warnings

from module import nifi_log
import settings


# Mode 기본 옵션 기준. None인 경우, development / None이 아닌 경우 production
NIFI_HOME = settings.NIFI_HOME


@dataclass
class Result():
    """
    NiFi 프로세스의 return에 대한 데이터 클래스 입니다.

    Arguments
    ---------
    result : Dict[str, Any]
        NiFi의 Attribute로 전달될 데이터입니다.
        키는 Attribute의 키가 되고 값은 Attribute의 값이 됩니다
    process_count : int, 1
        처리한 결과 건 수입니다.
    """
    result: Dict[str, Any]
    process_count: int = 1

@dataclass
class _TaskMetric():
    """
    작업결과에 대한 매트릭 정보의 데이터클래스 입니다.
    
    Arguments
    ---------
    process_name : str, ""
        프로세스명으로 데코레이터가 사용된 함수의 스크립트명이 작성됩니다.
    start_time : str, ""
        프로세스 시작 시간으로 포맷은 %Y-%m-%d %H:%M:%S.%f 로 작성됩니다.
    end_time : str, ""
        프로세스 종료 시간으로 포맷은 %Y-%m-%d %H:%M:%S.%f 로 작성됩니다.
    duration : float, 0
        프로세스 동작 시간입니다.
    status: Literal["success", "failure"], "failure"
        프로세스 결과 상태 값으로 Exception 발생 유무에 따라 success/failure 값이 작성됩니다.
    error: str, optional
        프로세스 에러 메세지입니다. 프로세스에서 발생한 Exception의 message 값으로 작성됩니다.
    """
    process_name: str = ""
    start_time: str = ""
    end_time: str = ""
    duration: float = 0
    status: Literal["success", "failure"] = "failure"
    error: Optional[str] = None


@dataclass
class _PipeOutput():
    """
    NiFi에 전달할 최종 결과 데이터 클래스입니다.

    Arguments
    ---------
    items: List[Result], []
        프로세스 반환 값
    metric: _TaskMetric
        프로세스 결과 정보
    """
    items: List[Result] = field(default_factory=list)
    metric: _TaskMetric = None


def _valid_mode(
        mode:Literal["development", "production", "debug", None]=None
) -> Literal["development", "production", "debug"]:
    """조건에 따라 모드 설정"""

    # 모드가 설정 되지 않은 경우, NIFI_HOME 유무에 따라 기본값 정의
    if mode is None:
        mode = "production" if NIFI_HOME else "development"

    # 잘못된 모드로 되어 있는 경우, 기본값 정의 (기본: development 모드)
    if mode not in ["development", "production", "debug"]:
        mode = "development"

    # 디버깅 모드
    if "-d" in sys.argv or "--debug" in sys.argv:
        mode = "debug"
        
    return mode

def _get_params_by_mode(mode:str) -> Dict[str, Any]:
    """모드별 파라미터 처리"""
    if mode == "production":
        # 프로덕션 모드
        # JSON 형태의 표준입력으로 파라미터를 받음
        stdin = sys.stdin.read()
        params = json.loads(stdin)

    else:
        # 그외 모드
        # 필수 파라미터 처리
        params = {}
        flowfile_uuid = str(uuid.uuid4())
        params.setdefault("path", "./")
        params.setdefault("filename", flowfile_uuid)
        params.setdefault("uuid", flowfile_uuid)
    
    return params

def _valid_output_structure(process_output: Any) -> List[Result]:
    """process의 output 검증"""
    results = []
    if process_output is None:
        results = [Result({}, 0)]
    elif isinstance(process_output, list):
        for output in process_output:
            if isinstance(output, dict):
                results.append(Result(result=output))
            elif isinstance(output, Result):
                results.append(output)
            else:
                # list 내부에 dict, Result가 아닌 경우 에러
                raise Exception(f"Invalid output type: {type(output)}")
    elif isinstance(process_output, dict):
        results = [Result(result=process_output)]
    elif isinstance(process_output, Result):
        results = [process_output]
    else:
        # list, dict, Result가 아닌 경우 에러
        raise Exception(f"Invalid output type: {type(process_output)}")

    return results


def _warning_message(message, category, filename, lineno, file=None, line=None):
    """Warning 문구를 logging으로 처리"""
    basename = os.path.basename(filename)
    logging.warning(f'{basename}:{lineno}: {category.__name__}: {message}')


def task(*, mode:Literal["development", "production", "debug", None]=None) -> Callable:
    """
    특정 `mode`를 기반으로 함수의 실행 모드를 설정하는 데코레이터입니다.
    데코레이트된 함수는 가변 위치 인자와 키워드 인자를 처리할 수 있어야 하며,
    dict, dict의 리스트, Result 객체, Result 객체의 리스트를 반환해야 합니다. 

    Parameters
    ----------
    mode : Literal["development", "production", "debug", None], optional
        데코레이트된 함수의 작동 모드를 지정합니다:
        
        development:
            - NiFi 환경이 아닌 Local 환경에서 스크립트를 테스트 하는 용도입니다.
            - 필요한 파라미터를 함수의 인자로 직접 받습니다.
            - 표준 출력(STDOUT)과 표준 오류(STDERR)에 제한 받지 않습니다.
        
        production:
            - NiFi 환경에서 ExecuteScript를 통해 서비스 하는 용도입니다.
            - 필요한 파라미터를 표준 입력(STDIN)을 통해 JSON 형식으로 받습니다.
            - 최종 결과를 제외하고 표준 출력(STDOUT)과 표준 오류(STDERR)이 출력되지 않습니다.
        
        debug:
            - 서비스 중인 스크립트를 디버깅 하는 용도입니다.
            - 필요한 파라미터를 표준 입력(STDIN)을 통해 JSON 형식으로 받습니다.
            - 표준 출력(STDOUT)과 표준 오류(STDERR)에 제한 받지 않습니다.
        
        None:
            - 조건에 따라 모드가 자동 설정 됩니다.
            - Python 스크립트 실행 시 -d 혹은 --debug 옵션을 줄 경우 debug로 설정 됩니다.
            - debug 모드가 아닌 경우, 환경 변수로 NIFI_HOME 가 있으면 production으로 설정 됩니다.
            - 그 외에 development로 설정 됩니다.


    Examples
    --------
    @task(mode="development")
    def compute(my_name: str, *args, **kwargs) -> Dict[str, Any]:
        # 함수 본문에서 인자와 `args`, `kwargs`를 직접 사용할 수 있습니다.
        print("필수 값:", my_name) # kim
        print("키워드 인자들:", kwargs) # {"uuid": "", "filename": ""}
        return {"greet": f"Hello, {my_name}!"}

    # 개발 모드에서는 인자로 값을 전달합니다.
    result = process(my_name="kim")
    # return 값으로 값을 받을 수 있습니다.
    print(result) # _Task(items=[Result(result={"greet": f"Hello, kim!"})])

    @task(mode="production")
    def process() -> List[Dict]:
        # 함수 본문은 STDIN을 통해 받은 JSON 입력을 파싱해야 합니다.
        print("데이터 처리:", data)
        return [{"처리된_데이터": item} for item in data]
    """
    def decorator(func:Callable[..., Union[Dict[str, Any], Iterable[Dict[str, Any]], Result, Iterable[Result]]]):
        process_name = os.path.basename(inspect.getfile(func)) # 호출한 스크립트 이름
        process_mode = _valid_mode(mode) # 모드 검증

        @wraps(func)
        @nifi_log.log(mode=process_mode, log_name=process_name)
        def wrapper(*args, **kwargs):
            
            # 모드에 따라 파라미터 받기
            params = _get_params_by_mode(process_mode)

            # 프로세스 초기값
            process_status: str = "failure"     # 프로세스 결과 상태 (success/failure)
            error_message: Optional[str] = None # 에러 메시지
            process_result: List[Result] = []   # 프로세스 결과

            # Warning 뜨는 거 처리
            warnings.showwarning = _warning_message

            # 프로세스 시작
            start_time = datetime.now() 
            logging.info(f"Process start: {start_time:%Y-%m-%d %H:%M:%S}")
            try:
                if process_mode == "production":
                    # Production 모드
                    # NiFi로 표준출력, 표준에러 되지 않게 제한
                    new_stdout = io.StringIO()
                    new_stderr = io.StringIO()
                    # 프로세스 실행
                    with redirect_stdout(new_stdout), redirect_stderr(new_stderr):
                        process_output = func(*args, **params, **kwargs)
                else:
                    # 그 외 모드
                    # 프로세스 실행
                    process_output = func(*args, **params, **kwargs)
                
                # 결과를 고정 포맷으로 변환 (List[Result])
                process_result = _valid_output_structure(process_output)

                # 프로세스 성공
                process_status = "success"

            except Exception as e:
                # 프로세스 실패
                traceback.print_exc(file=sys.stderr)
                error_message = str(e)
                process_status = "failure" 
                logging.error(f"An error occurred: {error_message}", exc_info=True)
                
            # 프로세스 종료
            end_time = datetime.now()
            logging.info(f"Process end: {end_time:%Y-%m-%d %H:%M:%S}")
            
            # NiFi로 보낼 결과값 작성
            process_metric = _TaskMetric(
                process_name=os.path.basename(inspect.getfile(func)),
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
                duration=(end_time-start_time).total_seconds(),
                status=process_status,
                error=error_message
            )
            result = _PipeOutput(
                items = process_result,
                metric= process_metric
            )

            # 결과값을 표준 출력으로 전송
            sys.stdout.write(json.dumps(asdict(result), indent=2, ensure_ascii=False))

            return result
        return wrapper
    return decorator