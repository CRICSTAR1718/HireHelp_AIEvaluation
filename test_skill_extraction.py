import httpx

headers = {
    "x-internal-service": "recruitment-service",
    "Content-Type": "application/json"
}
body = {
    "source_type": "resume",
    "source_id": "test-resume-1",
    "text": "John Doe is a senior Python developer with 5 years of experience in FastAPI, Django, and PostgreSQL. He has experience with cloud technologies like AWS and Docker."
}

print("Testing POST /api/v1/skill-extraction/extract (no focus_categories):")
try:
    response = httpx.post("http://localhost:8000/api/v1/skill-extraction/extract", headers=headers, json=body, timeout=60)
    print(f"Status: {response.status_code}")
    print(f"Content: {response.text}")
except Exception as e:
    print(f"Failed: {e}")
