

## 프로젝트 개요 📋

OtelMon은 OpenTelemetry를 활용하여 다양한 데이터 파이프라인 및 애플리케이션의 성능 모니터링과 분산 추적을 구현한 종합 모니터링 시스템입니다. 이 프로젝트는 Airflow, NiFi, FastAPI 등 여러 데이터 처리 도구들의 메트릭과 트레이스 데이터를 수집하고 시각화하여 시스템 운영 상태를 효율적으로 관리할 수 있도록 설계되었습니다.

## 시스템 아키텍처 🏗️

<img src="https://github.com/user-attachments/assets/2da5ad45-14a4-4100-8dda-6222ffe2015d" width="700"/>

## 사용 기술 🛠️

- **OpenTelemetry**: 분산 추적 및 메트릭 수집을 위한 통합 표준 프레임워크
- **Airflow**: 워크플로우 자동화 및 스케줄링 플랫폼
- **NiFi**: 데이터 수집, 변환, 전송을 위한 데이터 파이프라인 도구
- **FastAPI**: 고성능 Python API 서버
- **Docker & Docker Compose**: 컨테이너화 및 서비스 오케스트레이션
- **Tempo**: 분산 트레이싱 백엔드
- **Prometheus**: 메트릭 수집 및 모니터링 시스템
- **Grafana**: 데이터 시각화 및 모니터링 대시보드
- **MariaDB**: 관계형 데이터베이스 관리 시스템

## 주요 컴포넌트 ⚙️

### OpenTelemetry Collector 📡
- 다양한 서비스에서 생성된 트레이스와 메트릭 데이터 수집
- 데이터 처리 및 필터링
- Tempo, Prometheus로 데이터 전달
- HTTP POST 방식으로 FastAPI에 트레이스 데이터 전송

### Airflow ✈️
- 데이터 워크플로우 자동화 및 스케줄링
- OpenTelemetry SDK를 통한 워크플로우 성능 모니터링
- 작업 실행 추적 및 로깅
- `trace_log.py` 모듈을 통한 OpenTelemetry 계측 구현

### NiFi 🔄
- 데이터 파이프라인 구성 및 관리
- 실시간 데이터 처리 및 변환
- 데이터 흐름 모니터링
- ExecuteScript 프로세서를 사용한 Python 스크립트 실행
  - `ExecutePython.py`: Python 스크립트 실행을 위한 핵심 프로세서
  - `nifi.py`: OpenTelemetry 계측 및 트레이스 데이터 생성
  - Python 스크립트를 통한 데이터 처리 및 변환 로직 구현

### FastAPI ⚡
- OpenTelemetry Collector로부터 HTTP POST 방식으로 트레이스 정보 수신
- 트레이스 정보 분석 및 처리
- 실패한 프로세스 정보를 MariaDB에 저장
- 실패한 프로세스에 대한 알람 발송
- 트레이스 데이터 기반 모니터링 API 제공

### 모니터링 백엔드 📊
- **Tempo**: 분산 트레이싱 데이터 저장 및 쿼리
- **Prometheus**: 시계열 메트릭 데이터 수집 및 저장
- **Grafana**: 통합 대시보드를 통한 데이터 시각화

## 설치 및 실행 방법 🚀

1. 저장소 클론:
   ```bash
   git clone https://github.com/yourusername/OtelMon.git
   cd OtelMon
   ```

2. 환경 변수 설정:
   ```bash
   cp .env.example .env
   # .env 파일을 필요에 맞게 수정
   ```

3. Docker Compose를 사용하여 시스템 실행:
   ```bash
   docker-compose up -d
   ```

4. Airflow 컨테이너 실행 (별도로 실행):
   ```bash
   cd airflow
   docker-compose up -d
   ```

5. 서비스 접속:
   - Grafana: http://localhost:3000
   - Airflow: http://localhost:8080
   - NiFi: https://localhost:38443
   - FastAPI: http://localhost:8090/docs
   - Jaeger UI: http://localhost:16686
   - Prometheus: http://localhost:9090

## 네트워크 구성 🌐

이 프로젝트는 Docker 네트워크를 사용하여 서비스 간 통신을 구성합니다:

- **otel-network**: 모든 서비스가 공유하는 공통 네트워크
  - otelcol, tempo, prometheus, grafana, nifi, mariadb, fastapi 컨테이너가 포함
  - airflow 컨테이너들도 이 네트워크에 연결됨
  - 이 네트워크 내에서는 컨테이너 이름으로 서비스 접근 가능 (예: `otelcol:4317`)

- **네트워크 구성 단계**:
  1. 먼저 otel-network 생성:
     ```bash
     docker network create otel-network
     ```
  
  2. OtelMon 서비스 실행:
     ```bash
     docker-compose up -d
     ```
  
  3. Airflow 서비스 실행 (otel-network 공유):
     ```bash
     cd airflow
     docker-compose up -d
     ```

- **서비스 간 통신**:
  - 모든 서비스는 컨테이너 이름으로 직접 통신 가능
  - 예: Airflow에서 OpenTelemetry Collector 접근 시 `otelcol:4317` 사용
  - 별도의 호스트 IP 또는 호스트 이름 필요 없음

## 주요 구성 파일 📁

- **docker-compose.yaml**: 메인 서비스 구성 (OtelMon 컴포넌트)
- **airflow/docker-compose.yml**: Airflow 관련 서비스 구성
- **otelcol.yaml**: OpenTelemetry Collector 설정
- **tempo.yaml**: Tempo 설정
- **prometheus.yml**: Prometheus 설정
- **ExecutePython.py**: NiFi ExecuteScript 프로세서용 Python 실행기

## 시스템 스크린샷 📸

### 알람 이메일 📧
<img src="https://github.com/user-attachments/assets/42ae8cdf-868b-422c-8d2e-4b3a45badcf5" width="600"/>

### MariaDB 저장 데이터 💾
<img src="https://github.com/user-attachments/assets/454e507e-fa1c-4c14-b8a5-affbe4479b62" width="1000"/>


## 트러블슈팅 🔧

### 네트워크 연결 문제 🔌
- Docker 네트워크 설정 확인
- 컨테이너 이름으로 서비스 접근 (예: otelcol:4317)

### 로그 확인 📝
문제 진단을 위한
- OpenTelemetry Collector 로그: `docker logs otelcol`
- Airflow 로그: `docker logs airflow-webserver`
- FastAPI: `docker logs otelmon-api`

### Trace 전송 문제 📝
- trace_log.py의 span_processor 설정 확인
- force_flush() 호출 확인
- BatchSpanProcessor와 SimpleSpanProcessor 설정 검토
