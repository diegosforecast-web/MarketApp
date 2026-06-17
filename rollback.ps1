$revision = (gcloud run revisions list `
  --region=us-central1 `
  --service=market-forecast `
  --format="value(name)" | Select-Object -First 1)

Write-Host "Rolling back to $revision"

gcloud run services update-traffic market-forecast `
  --region=us-central1 `
  --to-revisions=$revision=100
