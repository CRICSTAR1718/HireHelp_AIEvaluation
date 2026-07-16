# Test SERVICE_TOKEN mode
# First test with wrong token
$headers = @{"Authorization"="Bearer wrong-token"; "Content-Type"="application/json"}
$body = '{"candidate_id":"test-cand-1","job_id":"test-job-1","resume_id":"test-resume-1","job_description":"Senior Python developer with FastAPI experience","candidate_skills":["Python","FastAPI","SQL"],"required_skills":["Python","FastAPI"],"candidate_experience_years":5.0,"required_experience_years":3.0,"candidate_education":[{"institution":"Test University","degree":"BS","field_of_study":"Computer Science","graduation_year":2020}]}'
Write-Host "Testing with WRONG service token:"
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/fitment-score/calculate" -Method POST -Headers $headers -Body $body -UseBasicParsing
    Write-Host "Success (should not happen):" $response.Content
} catch {
    Write-Host "Failed (expected):" $_.Exception.Message
}

# Then test with correct token
$headers = @{"Authorization"="Bearer test-secret-token"; "Content-Type"="application/json"}
Write-Host "`nTesting with CORRECT service token:"
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/fitment-score/calculate" -Method POST -Headers $headers -Body $body -UseBasicParsing
    Write-Host "Success:" $response.Content
} catch {
    Write-Host "Failed:" $_.Exception.Message
}
