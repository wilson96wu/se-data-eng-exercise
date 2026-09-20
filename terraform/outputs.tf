output "bucket_name" {
  value = var.bucket_name
}

output "bigquery_dataset_id" {
  value = google_bigquery_dataset.movies_data.dataset_id
}

output "airflow_gcs_service_account_email" {
  value = google_service_account.airflow_gcs.email
}


output "snowflake_schema_name" {
  value = snowflake_schema.wilson.name
}

output "snowflake_taxi_trips_raw_fqn" {
  value = "${snowflake_table.taxi_trips_raw.database}.${snowflake_table.taxi_trips_raw.schema}.${snowflake_table.taxi_trips_raw.name}"
}
