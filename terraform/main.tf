resource "google_storage_bucket" "landing" {
  name          = var.bucket_name
  location      = "US"
  force_destroy = false

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  versioning {
    enabled = true
  }
}
