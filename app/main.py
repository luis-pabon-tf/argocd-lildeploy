from fastapi import FastAPI

app = FastAPI(title="argocd-lildeploy")


@app.get("/")
def hello_world() -> dict[str, str]:
    return {"message": "Hello from GitOps! This deploy required zero manual steps."}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
