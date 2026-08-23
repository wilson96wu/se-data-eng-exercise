# Airflow + GCS Setup Guide (VS Code version)

This mirrors the PyCharm workflow from the task, but swaps in VS Code equivalents.

This repo's current layout is:

```
se-data-eng-exercise/
├── README.md
├── airflow_gcs_setup_guide.md
└── terraform/          # provisions the GCS bucket + BigQuery dataset used below
```

The steps below add a new `airflow/` folder at the repo root (sibling to `terraform/`)
to hold the Docker Compose setup and DAGs, so everything for the exercise lives in
one place.

The bucket and dataset referenced in Steps 3–4 are the ones provisioned by
`terraform/` (see `terraform/variables.tf` and `terraform/outputs.tf`):

- **GCP project**: `ee-sa-se-data` (`terraform/providers.tf`)
- **Bucket**: `sa-data-landing-wilson` (`var.bucket_name`)
- **BigQuery dataset**: `movies_data_wilson` (`var.dataset_id`)

Run `terraform apply` from `terraform/` first (or `terraform output bucket_name` if
it's already applied) to confirm these before using them below.

---

## 0. Prerequisites

- Docker Desktop installed and running
- VS Code installed, with these extensions:
  - **Dev Containers** (`ms-vscode-remote.remote-containers`) — this is the VS Code equivalent of PyCharm's "attach interpreter to a Docker Compose service"
  - **Python** extension
  - **Docker** extension (optional, but nice for viewing/starting containers from the sidebar)

---

## 1. Set up Airflow locally with Docker Compose

1. From the repo root, create the `airflow/` folder and `cd` into it in VS Code's terminal:
   ```bash
   mkdir -p airflow && cd airflow
   ```
2. Download the official compose file:
   ```bash
   curl -LfO 'https://airflow.apache.org/docs/apache-airflow/stable/docker-compose.yaml'
   ```
3. Create the required folders and `.env` file (from the same doc):
   ```bash
   mkdir -p ./dags ./logs ./plugins ./config
   echo -e "AIRFLOW_UID=$(id -u)" > .env
   ```
   Add `airflow/logs/`, `airflow/plugins/`, `airflow/config/`, and `airflow/.env` to
   the repo's `.gitignore` — they're runtime/container artifacts, not source. Keep
   `airflow/dags/` tracked since that's where the DAG code lives.
4. Set a `FERNET_KEY` in the same `.env` file. Without it, Docker Compose warns
   `"FERNET_KEY" variable is not set. Defaulting to a blank string`, and Airflow
   encrypts connection/variable secrets (e.g. the GCP keyfile JSON in Step 3) with
   a blank key instead of a real one. Generate a fresh key and append it:
   ```bash
   python3 -c "import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
   ```
   ```bash
   echo "FERNET_KEY=<paste the generated key here>" >> .env
   ```
   Generate your own key rather than reusing one from anywhere else — it's meant
   to be a private secret local to your setup.
5. **Give it 8GB RAM / 2 cores.** This is a Docker Desktop setting, not something you put in the compose file:
   - Open Docker Desktop → **Settings → Resources**
   - Set **Memory** to 8 GB and **CPUs** to 2
   - Apply & Restart Docker Desktop
6. Add the Google provider package so the GCS hook is available. Easiest way for local dev — add this line to `docker-compose.yaml` under the `x-airflow-common.environment` section:
   ```yaml
   _PIP_ADDITIONAL_REQUIREMENTS: apache-airflow-providers-google
   ```
7. Initialize and start:
   ```bash
   docker compose up airflow-init
   docker compose up -d
   ```
8. Wait a minute or two, then check all services are healthy:
   ```bash
   docker compose ps
   ```
9. Open the UI at [http://localhost:8080](http://localhost:8080) and log in with `airflow` / `airflow`.

---

## 2. Connect VS Code to the container (VS Code's version of the PyCharm step)

PyCharm links its interpreter to a running Compose service. In VS Code, you do this with **Dev Containers → Attach to Running Container**:

1. With `docker compose up -d` already running (from Step 1), open the Command Palette (`Cmd/Ctrl+Shift+P`).
2. Run **Dev Containers: Attach to Running Container...**
3. Pick the `airflow-scheduler` (or `airflow-worker`) container — these have your `dags/` folder mounted and the Python environment with the providers installed.
4. A new VS Code window opens *inside* that container. Open the folder `/opt/airflow` in it.
5. VS Code will prompt to install the Python extension inside the container — do that. It will auto-detect the container's Python interpreter (this is the equivalent of PyCharm's "web container interpreter").
6. Now when you write your DAG inside that attached window, you get real autocomplete/type-checking against the actual Airflow + provider packages installed in the container.

> Note: You still edit the files under `./dags` on your host machine (they're the same files, just mounted into the container at `/opt/airflow/dags`). You can just as easily edit them from your normal, non-attached VS Code window if you don't care about in-container autocomplete — Airflow will pick up any `.py` file dropped into `./dags`.

---

## 3. Configure the Airflow → GCS connection

1. Go to [http://localhost:8080/connection/list/](http://localhost:8080/connection/list/) and click **+**.
2. Fill in:
   - **Connection Id**: `google_cloud_default`
   - **Connection Type**: `Google Cloud`
   - **Project Id**: `ee-sa-se-data` (matches `terraform/providers.tf`)
   - **Keyfile JSON**: paste the full contents of the service account `keyfile.json` (get this from your team channel as noted in the task)
3. Click **Save**.

---

## 4. Write the `hello_world` DAG (TaskFlow API + GCSHook)

Create `airflow/dags/hello_world_gcs.py`:

```python
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
```

Notes:
- `GCSHook.upload()` takes a local `filename`, not raw bytes — that's why the task writes to `/tmp` first.
- `GCSHook.download()` returns bytes when no `filename` is given, which is why we `.decode()` before printing.
- The `>>` sets the dependency: write task must succeed before the read task runs.

---

## 5. Run and verify

1. In the Airflow UI, find `hello_world_gcs` in the DAGs list, unpause it (toggle on the left).
2. Trigger it manually (▶ button).
3. Click into the DAG run → `read_from_gcs` task → **Logs**. You should see `Hello, World!` printed.
4. Optionally confirm in the GCS console (or `gsutil ls gs://sa-data-landing-wilson/`) that `hello_world.txt` exists.

---

## Troubleshooting tips

- If the DAG doesn't appear in the UI, check `docker compose logs airflow-scheduler` for import errors (often a missing provider package — re-check Step 1.6 and re-run `docker compose up -d` after editing `_PIP_ADDITIONAL_REQUIREMENTS`, since it reinstalls on container start).
- If tasks fail with an auth error, double check the `google_cloud_default` connection's Keyfile JSON was pasted correctly (no extra quotes/escaping) and that the service account has Storage Object Admin (or equivalent) on the bucket.
