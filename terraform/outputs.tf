output "bucket_name" {
  value = var.bucket_name
}

output "bigquery_dataset_id" {
  value = google_bigquery_dataset.movies_data.dataset_id
}

output "airflow_gcs_service_account_email" {
  value = google_service_account.airflow_gcs.email
}
