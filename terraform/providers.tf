provider "google" {
  project = "ee-sa-se-data"
  region  = "us-central1"
}

provider "snowflake" {
  profile                   = var.snowflake_profile
  preview_features_enabled  = ["snowflake_table_resource"]
}
