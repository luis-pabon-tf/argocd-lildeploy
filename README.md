# argocd-lildeploy

Minimal FastAPI app for evaluating Argo CD as a CI/CD solution.

## Run locally

```sh
uv sync
uv run uvicorn app.main:app --port 8000
```

## Endpoints

- `GET /` — hello world
- `GET /health` — health check
