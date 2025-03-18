# etl_process.py
import random
import time
import decorators
import requests

@decorators.traced
def extract_data() -> decorators.Result:
    """
    파일/DB에서 데이터 추출 (가정)
    """
    print("extract_data")
    url = "http://apis.data.go.kr/1262000/OverviewEconomicService/OverviewEconomicList"
    params = {
        "serviceKey":"5uf4mJY2hv8gIwfKm5eECzvzzWdUckj4Ori+r9k0kjKe8Tgw0bRHzBBXped6NWRT+wuaTIaMPK2UN0Ji6KGbuA==",
        "pageNo":1,
        "numOfRows":10,
        "cond[country_nm::EQ]":"러시아",
        "cond[country_iso_alp2::EQ]":"RU"
    }
    response = requests.get(url, params=params)
    # params = {
    #     "serviceKey":"5uf4mJY2hv8gIwfKm5eECzvzzWdUckj4Ori+r9k0kjKe8Tgw0bRHzBBXped6NWRT+wuaTIaMPK2UN0Ji6KGbuA==",
    #     "pageNo":1,
    #     "numOfRows":300,
    # }
    # response = requests.get("http://apis.data.go.kr/B552696/ksight/riskindex", params=params, verify=False)
    print(response.history)
    print(response.status_code)
    print(response.text)
    
    row_count = response.json()['response']['body']['totalCount']
    
    return decorators.Result(
        result={},
        trace_metric={},
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
