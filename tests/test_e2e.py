import requests

data = {
    "premise": "A dog learns to fly.",
    "language": "English",
    "image_style": "Cinematic"
}

resp = requests.post("http://127.0.0.1:8000/generate-project", json=data)
print(f"Status: {resp.status_code}")
try:
    print(resp.json())
except:
    print(resp.text)
