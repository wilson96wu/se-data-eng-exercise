"""
Standalone example using the `google-cloud-storage` library directly,
with no Airflow involved.

Compare this to `dags/hello_world_gcs.py`, which does the same
upload/download using Airflow's `GCSHook` instead. The difference:

- Here, authentication comes from Application Default Credentials (ADC):
  either `gcloud auth application-default login` on your machine, or the
  `GOOGLE_APPLICATION_CREDENTIALS` env var pointing at a service account
  keyfile JSON.
- In the DAG, authentication comes from an Airflow Connection
  (`google_cloud_default`), configured once in the Airflow UI and reused
  by every task via `gcp_conn_id`.

Run directly with:
    python gcs_raw_client_example.py
"""

from google.cloud import storage

BUCKET_NAME = "sa-data-landing-wilson"  # from terraform/variables.tf (var.bucket_name)
OBJECT_NAME = "hello_world_raw_client.txt"
LOCAL_FILE_PATH = "/tmp/hello_world_raw_client.txt"


def write_to_gcs() -> None:
    with open(LOCAL_FILE_PATH, "w") as f:
        f.write("Hello, World! (via raw google-cloud-storage client)")

    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(OBJECT_NAME)
    blob.upload_from_filename(LOCAL_FILE_PATH)
    print(f"Uploaded gs://{BUCKET_NAME}/{OBJECT_NAME}")


def read_from_gcs() -> None:
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(OBJECT_NAME)
    content = blob.download_as_bytes()
    print(content.decode("utf-8"))


def list_bucket() -> None:
    client = storage.Client()
    print(f"Objects in gs://{BUCKET_NAME}:")
    for blob in client.list_blobs(BUCKET_NAME):
        print(f"  {blob.name} ({blob.size} bytes)")


if __name__ == "__main__":
    write_to_gcs()
    read_from_gcs()
    list_bucket()
