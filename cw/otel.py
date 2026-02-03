"""
OpenTelemetry instrumentation for Creative Workflow.

This module configures OpenTelemetry to send traces and logs to SigNoz.
It instruments Django and Celery automatically.
"""

import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor


def setup_opentelemetry():
    """Initialize OpenTelemetry instrumentation."""

    # Only setup if enabled
    if not os.getenv('OTEL_ENABLED', 'false').lower() == 'true':
        return

    # Resource identifies your service in SigNoz
    resource = Resource(attributes={
        "service.name": os.getenv('OTEL_SERVICE_NAME', 'creative-workflow'),
        "deployment.environment": os.getenv('ENVIRONMENT', 'development'),
    })

    # Configure tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # Configure OTLP exporter (sends data to SigNoz)
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4317'),
        insecure=True,
    )

    # Use batch processor for better performance
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Auto-instrument Django
    DjangoInstrumentor().instrument()

    # Auto-instrument Celery
    CeleryInstrumentor().instrument()

    # Auto-instrument Redis/Valkey
    RedisInstrumentor().instrument()

    # Auto-instrument logging (sends logs to traces)
    LoggingInstrumentor().instrument(set_logging_format=True)

    print("✓ OpenTelemetry instrumentation initialized - sending data to Jaeger")
