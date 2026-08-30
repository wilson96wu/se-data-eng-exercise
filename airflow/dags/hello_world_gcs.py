from __future__ import annotations

import pendulum
from airflow.decorators import dag, task
from airflow.providers.google.cloud.hooks.gcs import GCSHook

BUCKET_NAME = "sa-data-landing-wilson"  # from terraform/variables.tf (var.bucket_name)
OBJECT_NAME = "hello_world.txt"
LOCAL_FILE_PATH = "/tmp/hello_world.txt"
GCP_CONN_ID = "google_cloud_default"


@dag(
    dag_id="hello_world_gcs",
    schedule=None,
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,
    tags=["gcs", "example"],
)
def hello_world_gcs():

    @task
    def write_to_gcs() -> None:
        # GCSHook.upload uploads from a local file, so write it locally first
        with open(LOCAL_FILE_PATH, "w") as f:
            f.write("Hello, World!")

        hook = GCSHook(gcp_conn_id=GCP_CONN_ID)
        hook.upload(
            bucket_name=BUCKET_NAME,
            object_name=OBJECT_NAME,
            filename=LOCAL_FILE_PATH,
        )

    @task
    def read_from_gcs() -> None:
        hook = GCSHook(gcp_conn_id=GCP_CONN_ID)
        content = hook.download(
            bucket_name=BUCKET_NAME,
            object_name=OBJECT_NAME,
        )
        print(content.decode("utf-8"))

    write_to_gcs() >> read_from_gcs()


hello_world_gcs()
