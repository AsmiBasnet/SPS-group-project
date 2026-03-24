import requests
import json

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen3.5:4b",
        "prompt": 'Reply in JSON only: {"decision": "ANSWER", "answer": "2 weeks"}',
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0,
            "num_predict": 150
        }
    }
)

result = response.json()
print("Response:", result.get("response"))
print("Thinking:", result.get("thinking", "none"))