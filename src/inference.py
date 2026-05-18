"""FastAPI inference server for sentiment analysis."""

import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, generate_latest
from pydantic import BaseModel

from src.model import predict_sentiment
from src.preprocess import validate_input

app = FastAPI(title="ML Sentiment Analyzer", version="0.1.0")

# Prometheus metrics
REQUEST_COUNT = Counter(
    "prediction_requests_total",
    "Total number of prediction requests",
    ["method", "endpoint", "status"],
)
PREDICTION_LABEL_COUNT = Counter(
    "predictions_per_label_total",
    "Total predictions per sentiment label",
    ["label"],
)
REQUEST_LATENCY = Histogram(
    "prediction_request_duration_seconds",
    "Prediction request latency in seconds",
    ["method", "endpoint"],
)


class PredictRequest(BaseModel):
    text: str


class PredictResponse(BaseModel):
    label: str
    confidence: float


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/metrics")
def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    if not validate_input(request.text):
        REQUEST_COUNT.labels(method="POST", endpoint="/predict", status="400").inc()
        raise HTTPException(status_code=400, detail="Invalid input text")

    start = time.time()
    result = predict_sentiment(request.text)
    duration = time.time() - start

    REQUEST_COUNT.labels(method="POST", endpoint="/predict", status="200").inc()
    PREDICTION_LABEL_COUNT.labels(label=result["label"]).inc()
    REQUEST_LATENCY.labels(method="POST", endpoint="/predict").observe(duration)

    return PredictResponse(label=result["label"], confidence=result["confidence"])
