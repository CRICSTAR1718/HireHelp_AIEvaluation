import httpx

# Test 1: x-internal-service header with health endpoint (no auth required, but confirms header is accepted)
print("Test 1: GET /health with x-internal-service header:")
headers = {"x-internal-service": "recruitment-service"}
try:
    response = httpx.get("http://localhost:8000/health", headers=headers, timeout=60)
    print(f"Status: {response.status_code}")
    print(f"Content: {response.text}")
except Exception as e:
    print(f"Failed: {e}")

# Test 2: x-internal-service header with fitment endpoint (requires auth)
print("\nTest 2: POST /api/v1/fitment-score/calculate with x-internal-service header:")
headers = {
    "x-internal-service": "recruitment-service",
    "Content-Type": "application/json"
}
body = {
    "candidate_id": "test-cand-1",
    "job_id": "test-job-1",
    "resume_id": "test-resume-1",
    "job_description": "Senior Python developer",
    "candidate_skills": ["Python", "FastAPI"],
    "required_skills": ["Python"],
    "candidate_experience_years": 5.0,
    "required_experience_years": 3.0
}
try:
    response = httpx.post("http://localhost:8000/api/v1/fitment-score/calculate", headers=headers, json=body, timeout=60)
    print(f"Status: {response.status_code}")
    print(f"Content: {response.text[:500]}")
except Exception as e:
    print(f"Failed: {e}")

# Test 3: Invalid x-internal-service header
print("\nTest 3: POST /api/v1/fitment-score/calculate with INVALID x-internal-service header:")
headers = {
    "x-internal-service": "malicious-service",
    "Content-Type": "application/json"
}
try:
    response = httpx.post("http://localhost:8000/api/v1/fitment-score/calculate", headers=headers, json=body, timeout=60)
    print(f"Status: {response.status_code}")
    print(f"Content: {response.text}")
except Exception as e:
    print(f"Failed (expected): {e}")
