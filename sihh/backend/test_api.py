import requests
import json

api_key = "ed73a4a0e3b748239a32b59c12378bcb.NZem4TU_PCvEsEkFqItBhow7"

endpoints = [
    "https://api.ollama.com/v1/models",
    "https://api.ollama.ai/v1/models",
    "https://ollama.com/v1/models",
    "https://api.together.xyz/v1/models",
    "https://api.groq.com/openai/v1/models",
    "https://api.endpoints.anyscale.com/v1/models",
    "https://api.nebius.ai/v1/models"
]

for url in endpoints:
    print(f"Testing {url} ...")
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Success on {url}")
            break
    except Exception as e:
        print(f"Error: {e}")

