variable "bucket_name" {
  description = "sa data landing bucket for wilson"
  type        = string
  default     = "sa-data-landing-wilson"
}


variable "dataset_id" {
  description = "BigQuery dataset ID for raw movie data"
  type        = string
  default     = "movies_data_wilson"
}

variable "snowflake_profile" {
  description = "Name of the connection profile in ~/.snowflake/config to authenticate with"
  type        = string
  default     = "wilson"
}

variable "snowflake_database" {
  description = "Snowflake database for the raw layer"
  type        = string
  default     = "NEW_YORK_311"
}

variable "snowflake_schema_name" {
  description = "Per-user Snowflake schema for the raw layer"
  type        = string
  default     = "wilson"
}
