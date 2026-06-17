# Build version
$version = "v9"

Write-Host "=== Building image $version ==="
gcloud builds submit --tag gcr.io/diego-market-forecast/market-forecast:$version

Write-Host "=== Tagging image ==="
gcloud container images add-tag `
  gcr.io/diego-market-forecast/market-forecast:$version `
  gcr.io/diego-market-forecast/market-forecast:latest --quiet

gcloud container images add-tag `
  gcr.io/diego-market-forecast/market-forecast:$version `
  gcr.io/diego-market-forecast/market-forecast:staging --quiet

gcloud container images add-tag `
  gcr.io/diego-market-forecast/market-forecast:$version `
  gcr.io/diego-market-forecast/market-forecast:prod --quiet

Write-Host "=== Deploying to Cloud Run (prod) ==="
gcloud run deploy market-forecast `
  --image gcr.io/diego-market-forecast/market-forecast:prod `
  --region=us-central1 `
  --allow-unauthenticated

Write-Host "=== Triggering monthly job ==="
gcloud scheduler jobs run monthly-predictions --location=us-central1

Write-Host "=== Fetching logs ==="
gcloud logging read `
  "resource.type=cloud_run_revision AND resource.labels.service_name=market-forecast" `
  --limit=50 `
  --format="value(textPayload)"
