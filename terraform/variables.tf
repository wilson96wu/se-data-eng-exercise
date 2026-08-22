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
