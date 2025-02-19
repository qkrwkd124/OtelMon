import time
import csv
import datetime
import os

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace import Tracer
from opentelemetry.metrics import Meter


def csv_process(csv_file_path:str, tracer:Tracer, meter:Meter):
    
    # Metrics 준비
    # 카운터(Counter) : 처리된 레코드 수 누적
    records_counter = meter.create_counter(name="etl.records_processed_total", description="Total number of records processed in ETL", unit="1")
    
    # 히스토그램(Histogram) : ETL 실행 소요시간(초)
    etl_duration = meter.create_histogram(name="etl.job_duration", description="Duration of ETL process", unit="s")
    
    # 실패 횟수
    failure_counter = meter.create_counter(name="etl.failure_total", description="Total number of ETL failures", unit="1")

    with tracer.start_as_current_span("csv_process") as span:

        start_time = datetime.datetime.now()
        
        span.set_attribute("etl.file_path", csv_file_path)
        span.set_attribute("etl.process_id", os.getpid())

        csv_row_count = 0
        success_flag = False

        try:
            # ETL 로직직
            with open(csv_file_path, mode="r", encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    csv_row_count += 1

            time.sleep(2)
            success_flag = True

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            success_flag = False

        finally:
            end_time = datetime.datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            # span.set_attribute("etl.end_time", end_time)
            
            span.set_attribute("etl.duration", execution_time)
            span.set_attribute("etl.success_flag", success_flag)
            span.set_attribute("etl.csv_row_count", csv_row_count)

            if success_flag:
                span.set_status(StatusCode.OK)
                records_counter.add(csv_row_count)
                etl_duration.record(execution_time)




