FROM apache/airflow:2.5.3-python3.10


# Airflow Provider
RUN pip install --no-cache-dir \
        apache-airflow-providers-docker \
        apache-airflow-providers-mysql \
        apache-airflow-providers-sftp

# OpenTelemetry Requirements
COPY ./requirements.txt /opt
RUN pip install --no-cache-dir -r /opt/requirements.txt

USER airflow