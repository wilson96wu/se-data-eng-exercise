resource "google_bigquery_dataset" "movies_data" {
  dataset_id                 = var.dataset_id
  friendly_name              = "Movies Data - Raw Layer"
  description                = "Raw layer dataset for ingested movie data files, before cleaning/curation."
  location                   = "US"  # match your bucket's location/region
  delete_contents_on_destroy = false # safety: prevents accidental data loss on terraform destroy

  labels = {
    layer = "raw"
    owner = "wilson"
    env   = "dev"
  }
}
