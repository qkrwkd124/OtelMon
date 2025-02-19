import os
from src.monitoring.telmetry_config import init_telemetry, init_telemetry_otlp, init_meter, init_tracer
from src.etl.etl_process import etl_process
from src.etl.csv_process import csv_process


def main():
    init_telemetry_otlp()
    current_dir = os.path.dirname(os.path.abspath(__file__))

    csv_path = os.path.join(current_dir, "../data/data.csv")

    etl_process(csv_path)
    
def main2():
    
    meter = init_meter()
    tracer = init_tracer()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "../data/data.csv")
    
    csv_process(csv_path, tracer, meter)
    print("작업 완료")

if __name__ == "__main__":
    main2()
