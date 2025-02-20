# etl_process.py
import random
import time
import decorators

@decorators.traced
def extract_data() -> decorators.Result:
    """
    파일/DB에서 데이터 추출 (가정)
    """
    time.sleep(random.uniform(0.5, 1.0))
    row_count = random.randint(10, 100)
    source_info = "/home/study/data/data.csv"  # 혹은 DB info
    message = "Extracted data ok."
    
    return decorators.Result(
        result={},
        trace_metric={
            "etl.filepath": source_info,
            },
        process_count=row_count
    )

@decorators.traced
def transform_data(rows: int) -> decorators.Result:
    """
    변환 로직 (가정)
    """
    time.sleep(random.uniform(0.2, 0.8))
    # 랜덤으로 에러 발생 가정
    if random.random() < 0.2:
        # 에러 상황
        raise ValueError("Transform error!")
    filtered_rows = int(rows * 0.9)
    return decorators.Result(
        result={},
        trace_metric={},
        process_count=filtered_rows
    )

@decorators.traced
def load_data(rows: int) -> decorators.Result:
    """
    적재 로직 (가정)
    """
    time.sleep(random.uniform(0.3, 0.6))
    return decorators.Result(
        result={},
        trace_metric={},
        process_count=rows
    )

if __name__ == "__main__":
    try :
        extract_data()
        load_data(100)
        transform_data(100)
    except Exception as e:
        print(f"Error: {e}")
