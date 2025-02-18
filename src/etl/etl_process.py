import time
import csv
import datetime
import os

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode



def etl_process(csv_file_path:str):
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("etl_process") as span:

        start_time = datetime.datetime.now()

        span.set_attribute("etl.start_time", start_time)
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
            span.set_attribute("etl.end_time", end_time)
            span.set_attribute("etl.duration", (end_time - start_time).total_seconds())
            span.set_attribute("etl.success_flag", success_flag)
            span.set_attribute("etl.csv_row_count", csv_row_count)

            if success_flag:
                span.set_status(Status(StatusCode.OK, "ETL Process Success"))




