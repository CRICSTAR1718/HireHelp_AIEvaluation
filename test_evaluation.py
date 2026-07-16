import httpx

headers = {
    "x-internal-service": "recruitment-service",
    "Content-Type": "application/json"
}
body = {
    "application_id": "test-app-1",
    "candidate_id": "test-cand-1",
    "job_id": "test-job-1",
    "resume_url": "http://example.com/resume.pdf",
    "job_description": "Senior Python developer with FastAPI experience",
    "required_skills": ["Python", "FastAPI"],
    "required_experience_years": 3.0
}

print("Testing POST /api/v1/evaluation:")
try:
    response = httpx.post("http://localhost:8000/api/v1/evaluation", headers=headers, json=body, timeout=60)
    print(f"Status: {response.status_code}")
    print(f"Content: {response.text}")
except Exception as e:
    print(f"Failed: {e}")
