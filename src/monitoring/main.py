import os
from src.monitoring.telmetry_config import init_telemetry
from src.etl.etl_process import etl_process



def main():
    init_telemetry()
    current_dir = os.path.dirname(os.path.abspath(__file__))

    csv_path = os.path.join(current_dir, "../data/data.csv")

    etl_process(csv_path)

if __name__ == "__main__":
    main()
