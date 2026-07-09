from fastapi import FastAPI

app = FastAPI(title="argocd-lildeploy")


@app.get("/")
def hello_world() -> dict[str, str]:
    return {"message": "Hello World!"}


@app.get("/bye")
def goodbye_world() -> dict[str, str]:
    return {"message": "Bye! This should still not require any manual steps..."}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
