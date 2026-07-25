import requests 
import json
from app.translate import to_text
from pydantic import BaseModel, Field, ValidationError
from typing import Literal
from app.schema import Meta
import os

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

url = f"{OLLAMA_HOST}/api/chat"

SYSTEM_PROMPT = """ You are a determinsitc behavioral classifier peresent in a software pipeline\
You are not a chatbot and must never converse, explain.
You will be given one day of workplace Meta data for one employeee. 
Classify the employee's state into exactly one category using these calibration ranges:
- FOCUS: 0-4 meetings, 0-4 meeting hours, gaps of 20-90 minutes, 0-2 messages \
after 8pm, 0-5 context switches per hour.
- NEUTRAL: 4-8 meetings, 3.5-8 meeting hours, gaps of 10-48 minutes, 4-14 \
messages after 8pm, 3-10 context switches per hour.
- BURNOUT: 7-12 meetings, 7-12 meeting hours, gaps of 1-5 minutes, 8-25 \
messages after 8pm, 7-15 context switches per hour.
When features disagree, pick the category matching the majority of the five \
features.

Respond with ONLY a JSON object of this exact shape:
{"classification" : "<FOCUS|NEUTRAL|BURNOUT>", "score": <confidence score between 0.0 and 1.0>}
"""
MAX_ATTEMPTS = 3


class Result(BaseModel):
    classification : Literal["FOCUS", "NEUTRAL", "BURNOUT"]
    score : float = Field(ge=0.0, le=1.0)

def chat(log: Meta, model: str = "qwen3:4b-instruct", stream: bool = False) -> dict:
    prompt = to_text(log)
    messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    last_error : Exception | None = None

    for attempt in range(MAX_ATTEMPTS):
        text = {
            "model": model,
            "messages" : messages,
            "stream": stream,
            "options": {
                "temperature": 0.0
            },
            "format": Result.model_json_schema()
        }

        response = requests.post(url=url, json=text)

        if response.status_code != 200:
            print("Error")
            response.raise_for_status()
    
        data = response.json()["message"]["content"]

        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as e :
            last_error = e
            #feeding back the bad output and the correction back to the model
            messages.append({"role": "assistant", "content": data})
            messages.append({
                "role": "user",
                "content": (
                    "Your previous response was invalid: "
                    f"Respond again with ONLY the "
                    "JSON object in the required shape, nothing else."
                ),
            })
            continue

        try:
            Result.model_validate(parsed)
            return parsed
        except ValidationError as exc:
            last_error = exc
            messages.append({"role": "assistant", "content": data})
            messages.append({
                "role": "user",
                "content": (
                    "Your JSON was syntactically valid, but the content was wrong: "
                    f"{exc}. Classification must be exactly one of FOCUS, NEUTRAL, "
                    "or BURNOUT, and score must be a number between 0.0 and 1.0. "
                    "Respond again with ONLY the corrected JSON object."
                ),
            })
    raise last_error

if __name__ == "__main__":
    import datetime

    sample = Meta(
        user_id="test-user",
        date=datetime.date(2026, 7, 10),
        total_meetings=1,
        meeting_hours_per_day=1,
        average_gap_between_meetings_minutes=0,
        messages_sent_after_8pm=2,
        context_switches_per_hour=5,
    )

    result = chat(log = sample)

    print(f"{result}")
