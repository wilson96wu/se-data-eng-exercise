resource "google_service_account" "airflow_gcs" {
  account_id   = "airflow-gcs-sa-wilson"
  display_name = "Airflow GCS access (hello_world_gcs DAG)"
  description  = "Least-privilege identity for the local Airflow instance to read/write the landing bucket."
}

resource "google_storage_bucket_iam_member" "airflow_gcs_object_admin" {
  bucket = google_storage_bucket.landing.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.airflow_gcs.email}"
}
