import logging
import requests

import module.nifi as nifi
import module.trace_log as trace_log

@nifi.task(mode="production")
@trace_log.traced()
def extract(*args, **kwargs) :
    logging.info("===== extract start =====")

    url = "http://apis.data.go.kr/1262000/OverviewEconomicService/OverviewEconomicList"
    params = {
        "serviceKey":"5uf4mJY2hv8gIwfKm5eECzvzzWdUckj4Ori+r9k0kjKe8Tgw0bRHzBBXped6NWRT+wuaTIaMPK2UN0Ji6KGbuA==",
        "pageNo":1,
        "numOfRows":10,
        "cond[country_nm::EQ]":"러시아",
        "cond[country_iso_alp2::EQ]":"RU"
    }
    response = requests.get(url, params=params)
    logging.info(response.status_code)
    logging.info(response.text)

    row_count = response.json()['response']['body']['totalCount']
    logging.info(args)
    logging.info(kwargs)
    logging.info(f"group_name : {kwargs.get('group_name')}")
    logging.info(f"process_name : {kwargs.get('process_name')}")

    return nifi.Result(
        result={},
        process_count=row_count
    )

if __name__ == "__main__":
    extract()
    