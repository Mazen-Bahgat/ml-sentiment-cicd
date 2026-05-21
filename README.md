# ml-sentiment-app 

> **FastAPI sentiment analysis service** — containerised, fully tested, and shipped through an automated CI pipeline on Gitea Actions.

Part of a two-repo DevOps platform built for **CISC 814 — DevOps and Continuous Delivery** at Queen's University (Summer 2026).
The companion **GitOps / deployment repo** lives at [`team-4-gitops`](https://github.com/Mazen-Bahgat/devops-sentiment-k8s-gitops) and handles everything from Kubernetes manifests to canary rollouts and Grafana dashboards.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Repository Structure](#repository-structure)
- [API Reference](#api-reference)
- [CI Pipeline](#ci-pipeline)
- [Docker](#docker)
- [Local Development](#local-development)
- [Testing & Code Quality](#testing--code-quality)
- [Configuration](#configuration)
- [Related Repository](#related-repository)
- [Team](#team)

---

## Overview

`ml-sentiment-app` is a lightweight ML inference service that wraps a **TextBlob** sentiment classifier behind a **FastAPI** REST API. It exposes a `/predict` endpoint, a `/health` probe, and **Prometheus metrics** for observability.

The service is designed to be:

- **Stateless** — horizontally scalable on Kubernetes
- **Observable** — native Prometheus instrumentation (request rate, error rate, latency histograms)
- **Quality-gated** — every push triggers linting, type checking, 100 % test coverage, a Docker build, and SBOM generation before any image reaches the registry

---

## Architecture

The diagram below shows the full platform. This repo owns everything in the **CI layer** (top half). The GitOps / deployment layer (bottom half) is managed in the companion repo.


![CI/CD Pipeline Architecture](https://raw.githubusercontent.com/Mazen-Bahgat/devops-sentiment-k8s-gitops/main/devops-diagram.svg)

> **Full platform diagram** (including the GitOps / Kubernetes / monitoring layer) is available in the [companion repo](https://github.com/Mazen-Bahgat/devops-sentiment-k8s-gitops#architecture).

---

## Repository Structure

```
ml-sentiment-app/
├── src/
│   ├── inference.py        # FastAPI app, route handlers, Prometheus metrics
│   ├── model.py            # TextBlob sentiment classifier wrapper
│   └── preprocess.py       # Text cleaning and input validation
├── tests/
│   ├── test_inference.py   # API-level tests (FastAPI TestClient)
│   ├── test_model.py       # Unit tests for the classifier
│   └── test_preprocess.py  # Unit tests for preprocessing logic
├── .gitea/
│   └── workflows/
│       └── ci.yml          # 7-step Gitea Actions CI pipeline
├── Dockerfile              # Multi-stage build (builder + slim runtime)
├── requirements.txt        # Runtime dependencies
├── pyproject.toml          # Mypy config (disallow_untyped_defs = true)
└── README.md
```

---

## API Reference

### `GET /health`

Returns service health status. Used as a Kubernetes liveness and readiness probe.

```json
// Response 200
{ "status": "ok" }
```

### `POST /predict`

Runs sentiment analysis on the provided text.

**Request body:**

```json
{ "text": "The product is absolutely fantastic!" }
```

**Response:**

```json
{
  "label": "positive",
  "polarity": 0.625,
  "subjectivity": 0.6
}
```

| Field | Type | Description |
|---|---|---|
| `label` | string | `positive` / `negative` / `neutral` |
| `polarity` | float | Score in `[-1.0, 1.0]` |
| `subjectivity` | float | Score in `[0.0, 1.0]` |

**Error responses:**

| Code | Meaning |
|---|---|
| `422` | Validation error — missing or malformed body |
| `500` | Internal server error |

### `GET /metrics`

Exposes Prometheus metrics in the standard text format. Scraped by the ServiceMonitor in the cluster every 15 seconds.

| Metric | Type | Labels |
|---|---|---|
| `prediction_requests_total` | Counter | `method`, `endpoint`, `status` |
| `predictions_per_label_total` | Counter | `label` |
| `prediction_request_duration_seconds` | Histogram | `method`, `endpoint` |

---

## CI Pipeline

The pipeline is defined in `.gitea/workflows/ci.yml` and runs automatically on every **push**, **pull request**, and **tag** to `main`. Branch protection is enabled — merging to `main` requires a passing CI run.

| Step | Tool | Command | Artefact |
|---|---|---|---|
| 1 | Setup | Install deps + download TextBlob corpora + `/health` check | — |
| 2 | Linting | `ruff check src/ tests/` | `ruff-report.txt` |
| 3 | Type checking | `mypy src/` | `mypy-report.txt` |
| 4 | Tests + coverage | `pytest --cov=src --cov-report=term-missing` (≥ 70 % required) | `pytest-report.txt`, `coverage.xml` |
| 5 | Docker build | `docker build -t ml-sentiment-app .` | — |
| 6 | Docker push | Push `:latest` + `:<git-sha>` to registry | — |
| 7 | SBOM | `syft image -o spdx-json` | `sbom.spdx.json` |

All artefacts are uploaded as `ci-reports-${{ gitea.run_id }}` and attached to each Actions run.

**Coverage result:** 14/14 tests pass at **100 % coverage** across `inference.py`, `model.py`, and `preprocess.py`.

---

## Docker

The `Dockerfile` uses a **two-stage build** to keep the production image lean:

| Property | Value |
|---|---|
| Base image | `python:3.11-slim` (both stages) |
| Build stage | Installs all dependencies + downloads TextBlob corpora |
| Runtime stage | Copies only installed packages and `src/`; no build tools |
| User | `appuser` (non-root, created at build time) |
| Exposed port | `8000` |
| Entry point | `uvicorn src.inference:app --host 0.0.0.0 --port 8000` |

**Build and run locally:**

```bash
docker build -t ml-sentiment-app .
docker run -p 8000:8000 ml-sentiment-app
```

**Image tags pushed by CI:**

```
localhost:5001/ml-sentiment-app:latest
localhost:5001/ml-sentiment-app:<git-sha>
```

---

## Local Development

**Prerequisites:** Python 3.11+, `pip`

```bash
# 1. Clone
git clone https://github.com/Mazen-Bahgat/ml-sentiment-cicd.git
cd ml-sentiment-cicd

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download TextBlob corpora (one-time)
python -m textblob.download_corpora

# 5. Start the development server
uvicorn src.inference:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs (Swagger UI) at `http://localhost:8000/docs`.

---

## Testing & Code Quality

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=src --cov-report=term-missing

# Linting
ruff check src/ tests/

# Type checking
mypy src/
```

Mypy is configured in `pyproject.toml` with `disallow_untyped_defs = true` — all functions must carry full type annotations.

---

## Configuration

The application reads the following environment variables (defaults shown):

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | Runtime environment (`production` / `development`) |
| `LOG_LEVEL` | `info` | Uvicorn log level |

In the cluster these are injected via a Kubernetes **ConfigMap** (`APP_ENV=production`, `LOG_LEVEL=info`). See the [GitOps repo](https://github.com/Mazen-Bahgat/devops-sentiment-k8s-gitops) for details.

---

## Related Repository

| Repo | Purpose |
|---|---|
| **This repo** — [`ml-sentiment-cicd`](https://github.com/Mazen-Bahgat/ml-sentiment-cicd) | Application source code, CI pipeline, Dockerfile |
| [`devops-sentiment-k8s-gitops`](https://github.com/Mazen-Bahgat/devops-sentiment-k8s-gitops) | Kubernetes manifests, ArgoCD, Kustomize, Argo Rollouts, Prometheus, Grafana |

---

## Team

**CISC 814 — Team 4 · Queen's University, Summer 2026**

| Member | Student ID | Part A Focus | Part B Focus |
|---|---|---|---|
| Hana Amrya | 25tvtm | Repo setup, branch protection, Ruff linting | Cluster setup, base K8s manifests, Grafana latency panel |
| Hassan Albattra | 25vhsj | Mypy type checking, pytest + coverage | Rollout resource, production overlay, ServiceMonitor |
| Mazen Bahgat | 25dtg4 | Infrastructure, Dockerfile | GitOps repo, ArgoCD, canary step design |
| Mariam Mousa | 25qns4 | Docker build + push, Syft SBOM | Prometheus metrics, canary traffic testing, Grafana error panel |

---

> **Demo video:** [Full end-to-end deployment walkthrough](https://drive.google.com/file/d/1JrWXD9OctY18s7I3XvVHQgY5bruHw9RI/view?usp=sharing) — CI trigger → Docker push → ArgoCD sync → canary rollout → live Grafana dashboard (10 min).
