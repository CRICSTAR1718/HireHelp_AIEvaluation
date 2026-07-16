import httpx

headers = {
    "x-internal-service": "recruitment-service",
    "Content-Type": "application/json"
}
body = {
    "interview_id": "test-interview-1",
    "question_index": 0,
    "question": "Can you explain your experience with Python and FastAPI?",
    "answer": "I have 5 years of experience with Python, including 2 years specifically with FastAPI. I've built several REST APIs using FastAPI, including a microservices architecture for a fintech application. I'm familiar with dependency injection, async/await patterns, and Pydantic models for validation.",
    "question_category": "technical",
    "evaluation_rubric": {
        "technical_accuracy": "Should demonstrate understanding of Python and FastAPI concepts",
        "depth": "Should provide specific examples and details",
        "clarity": "Should be clear and well-structured"
    }
}

print("Testing POST /api/v1/answer-evaluation/evaluate:")
try:
    response = httpx.post("http://localhost:8000/api/v1/answer-evaluation/evaluate", headers=headers, json=body, timeout=60)
    print(f"Status: {response.status_code}")
    print(f"Content: {response.text}")
except Exception as e:
    print(f"Failed: {e}")
