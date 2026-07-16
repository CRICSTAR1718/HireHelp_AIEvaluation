$headers = @{"x-internal-service"="recruitment-service"; "Content-Type"="application/json"}
$body = '{"application_id":"test-app-1","candidate_id":"test-cand-1","job_id":"test-job-1","resume_url":"http://example.com/resume.pdf","job_description":"Senior Python developer"}'
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/evaluation" -Method POST -Headers $headers -Body $body -UseBasicParsing
    Write-Host "Success:" $response.Content
} catch {
    $err = $_.Exception
    Write-Host "Failed:" $err.Message
    if ($err.Response) {
        Write-Host "Status:" $err.Response.StatusCode.value__
        Write-Host "Content:" $err.Response.GetResponseStream()
    }
}
