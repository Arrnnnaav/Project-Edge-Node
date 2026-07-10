import requests 
import json
import time

url = "http://localhost:11434/api/chat"

model = "qwen3:4b-instruct"

def non_streaming(prompt: str) -> dict:
    text = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {
            "temperature": 0.0,
        }
    }

    start_time = time.time()

    response = requests.post(url, json=text)

    end_time = time.time()

    print(response.status_code)

    data = response.json()
    total_time = end_time - start_time

    return {
    "mode": "non-streaming",
    "total_time": total_time,
    "ttft": total_time,
    "text": data["message"]["content"]
}

def run_streaming(prompt: str) -> dict:
    text = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "options": {
            "temperature": 0.0,
        }
    }

    start_time = time.time()
    first_token_time = None
    full_text = ""

    with requests.post(url, json=text, stream=True) as response:
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue

            chunk = json.loads(line)

            if first_token_time is None:
                first_token_time = time.time() - start_time

            content_piece = chunk.get("message", {}).get("content", "")
            full_text += content_piece

            if chunk.get("done"):
                break

    end_time = time.time()
    total_time = end_time - start_time

    return {
        "mode": "streaming",
        "total_time": total_time,
        "ttft": first_token_time,
        "text": full_text
    }

def print_result(result: dict):
    print(f"\n--- {result['mode'].upper()} ---")
    print(f"Time to First Token: {result['ttft']:.3f}s")
    print(f"Total time:          {result['total_time']:.3f}s")
    print(f"Response text:       {result['text'][:100]}...")


if __name__ == "__main__":
    test_prompt = "Explain in 3 sentences why offline AI inference matters for privacy."

    print("Running non-streaming request...")
    non_stream_result = non_streaming(test_prompt)
    print_result(non_stream_result)

    print("\nRunning streaming request...")
    stream_result = run_streaming(test_prompt)
    print_result(stream_result)

    print("\n=== COMPARISON ===")
    print(f"Non-streaming TTFT: {non_stream_result['ttft']:.3f}s   |   Streaming TTFT: {stream_result['ttft']:.3f}s")
    print(f"Non-streaming total: {non_stream_result['total_time']:.3f}s  |   Streaming total: {stream_result['total_time']:.3f}s")