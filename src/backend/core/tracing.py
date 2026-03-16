"""
OpenTelemetry distributed tracing configuration.

Instruments FastAPI, SQLAlchemy, and Redis automatically.
Set OTLP_ENDPOINT to export traces to Jaeger, Tempo, or any OTLP-compatible backend.
When OTLP_ENDPOINT is empty the SDK runs with a no-op exporter (zero overhead).
"""

import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

logger = logging.getLogger(__name__)


def _build_resource(service_name: str, service_version: str) -> Resource:
    return Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": "production",
    })


def setup_tracing(
    app,
    service_name: str = "delivery-intelligence-platform",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    db_engine=None,
) -> None:
    """
    Configure OpenTelemetry tracing and attach instrumentation to the FastAPI app.

    Args:
        app:              FastAPI application instance.
        service_name:     Logical service name reported in traces.
        service_version:  Service version tag.
        otlp_endpoint:    OTLP HTTP endpoint, e.g. "http://jaeger:4318".
                          When None or empty, a Console exporter is used in dev
                          and a no-op in production.
        db_engine:        Optional SQLAlchemy async engine to instrument.
    """
    resource = _build_resource(service_name, service_version)
    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces")
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info(f"OpenTelemetry: OTLP exporter configured → {otlp_endpoint}")
        except ImportError:
            logger.warning(
                "opentelemetry-exporter-otlp-proto-http not installed. "
                "Falling back to ConsoleSpanExporter."
            )
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    else:
        # Development: log spans to console so developers can see traces without
        # running a collector.  In production set OTLP_ENDPOINT.
        logger.info("OpenTelemetry: no OTLP_ENDPOINT set, using ConsoleSpanExporter (dev mode)")
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)

    # --- FastAPI instrumentation ---
    FastAPIInstrumentor.instrument_app(app)

    # --- Redis instrumentation ---
    try:
        RedisInstrumentor().instrument()
        logger.info("OpenTelemetry: Redis instrumented")
    except Exception as e:
        logger.warning(f"OpenTelemetry: Redis instrumentation failed: {e}")

    # --- SQLAlchemy instrumentation (if engine provided) ---
    if db_engine is not None:
        try:
            SQLAlchemyInstrumentor().instrument(engine=db_engine.sync_engine)
            logger.info("OpenTelemetry: SQLAlchemy instrumented")
        except Exception as e:
            logger.warning(f"OpenTelemetry: SQLAlchemy instrumentation failed: {e}")

    logger.info(f"OpenTelemetry tracing initialised for service '{service_name}'")


def get_tracer(name: str = "delivery-intelligence-platform") -> trace.Tracer:
    """Convenience helper to get a named tracer anywhere in the codebase."""
    return trace.get_tracer(name)
