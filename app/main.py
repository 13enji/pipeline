from fastapi import FastAPI

app = FastAPI(title="Pipeline", version="0.1.0")


@app.get("/hello")
def hello() -> dict[str, str]:
    return {"message": "Hello, World"}
