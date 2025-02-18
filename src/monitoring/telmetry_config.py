import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode
# from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


def init_telemetry():

    # 전역 TracerProvider 설정
    provider = TracerProvider()

    # Exporter 등록(예: 콘솔)
    console_exporter = ConsoleSpanExporter()
    span_processor = BatchSpanProcessor(console_exporter)
    provider.add_span_processor(span_processor)

    trace.set_tracer_provider(provider)
    
    return provider
    





