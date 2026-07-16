# Test with valid JWT token (using test-secret-key)
$jwtToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZXJ2aWNlIjoidGVzdC1zZXJ2aWNlIiwic3ViIjoidGVzdC11c2VyIiwicm9sZXMiOlsiYWRtaW4iXX0.aY7-IZNE5HI93JJruKyguUrzC5nCbwgkQxtPk-p40hM"
$headers = @{"Authorization"="Bearer $jwtToken"; "Content-Type"="application/json"}
$body = '{"candidate_id":"test-cand-1","job_id":"test-job-1","resume_id":"test-resume-1","job_description":"Senior Python developer with FastAPI experience","candidate_skills":["Python","FastAPI","SQL"],"required_skills":["Python","FastAPI"],"candidate_experience_years":5.0,"required_experience_years":3.0,"candidate_education":[{"institution":"Test University","degree":"BS","field_of_study":"Computer Science","graduation_year":2020}]}'
Write-Host "Testing with valid JWT token (secret: test-secret-key):"
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/fitment-score/calculate" -Method POST -Headers $headers -Body $body -UseBasicParsing
    Write-Host "Success:" $response.Content
} catch {
    Write-Host "Failed:" $_.Exception.Message
}
