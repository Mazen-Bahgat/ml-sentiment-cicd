FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime

WORKDIR /app

RUN useradd --create-home --shell /bin/bash appuser

COPY --from=builder /install /usr/local
COPY src/ ./src/

RUN python -m textblob.download_corpora

USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.inference:app", "--host", "0.0.0.0", "--port", "8000"]