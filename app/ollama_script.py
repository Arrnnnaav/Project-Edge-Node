import requests 
import json

url = "http://localhost:11434/api/chat"

def chat(prompt: str, model: str = "qwen3:4b-instruct", stream: bool = False) -> str:
    text = {
        "model": model,
        "messages" :[
            {"role": "system", "content": "You must respond only with valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "stream": stream,
        "options": {
            "temperature": 0.0
        },
        "format": "json"
    }

    response = requests.post(url=url, json=text)

    print (response.status_code)
    if response.status_code != 200:
        print("Error")
        response.raise_for_status()
    
    data = response.json()
    return data["message"]["content"]

if __name__ == "__main__":
    prompt = "HI"
    Nonstream = chat(prompt=prompt, stream = False)

    print(Nonstream)
