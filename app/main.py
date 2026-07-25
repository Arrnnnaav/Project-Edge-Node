from fastapi import FastAPI, HTTPException

from app.schema import Meta
from app.ollama_script import chat, Result

app = FastAPI(title="Project Edge-Node")


@app.post("/analyze_telemetry", response_model=Result)
def analyze_telemetry(log: Meta) -> Result:
    try:
        return chat(log=log)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Classification failed: {exc}",
        )