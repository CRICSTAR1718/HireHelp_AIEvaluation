# Test current behavior with x-internal-service header (no Authorization)
$headers = @{"x-internal-service"="recruitment-service"; "Content-Type"="application/json"}
$body = '{"application_id":"test-app-1","candidate_id":"test-cand-1","job_id":"test-job-1","resume_url":"http://example.com/resume.pdf","job_description":"Senior Python developer"}'
Write-Host "Testing POST /api/v1/evaluation with x-internal-service header (no Authorization):"
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/evaluation" -Method POST -Headers $headers -Body $body -UseBasicParsing
    Write-Host "Success:" $response.Content
} catch {
    Write-Host "Failed (expected 403):" $_.Exception.Message
    Write-Host "Status:" $_.Exception.Response.StatusCode.value__
}
