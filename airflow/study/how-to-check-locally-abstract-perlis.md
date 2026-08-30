# How to locally verify `my_old_dag.py` fails to parse

## Context
`airflow/dags/my_old_dag.py` instantiates `BaseBranchOperator()` directly (line 26) with no `task_id` and no `choose_branch()` override, which is invalid usage and throws at DAG-parse time. That's why the DAG never appears in the Airflow web UI — it's silently rejected as a broken DAG. The user wants a way to *locally* reproduce/confirm this parse failure, without needing to spin up the full Docker stack and dig through the UI each time.

The repo's Airflow setup (confirmed via exploration):
- Runs via `airflow/docker-compose.yaml` (official Airflow 3.3.1 image, CeleryExecutor), documented in `airflow_gcs_setup_guide.md`. DAGs bind-mount from `airflow/dags` → `/opt/airflow/dags`.
- There's also a local `airflow/.venv` (gitignored) built with airflow 3.3.1 + `apache-airflow-providers-standard` 1.17.0 + `apache-airflow-providers-google` 22.3.0, intended for editor support / local package resolution.
- No requirements.txt/pyproject.toml, no Makefile, no pytest DagBag import-error tests exist in the repo today.

## Recommended approach: three ways to check, fastest first

### 1. Fastest — run the file directly with the local venv's Python
```bash
cd /Users/wilsonwu/projects/terraform/se-data-eng-exercise
airflow/.venv/bin/python airflow/dags/my_old_dag.py
```
Since the DAG file has no `if __name__ == "__main__"` guard, Python just executes the module top-to-bottom, hitting the same `BaseBranchOperator()` line and raising the same `TypeError` Airflow would hit during parsing. This needs no Docker containers running and gives instant feedback (~1-2s). This is the way to check it *right now, standalone*.

### 2. Closest to what Airflow itself does — Airflow's own DagBag loader
```bash
cd /Users/wilsonwu/projects/terraform/se-data-eng-exercise/airflow
.venv/bin/python -c "
from airflow.models import DagBag
bag = DagBag(dag_folder='dags')
for filename, err in bag.import_errors.items():
    print(filename)
    print(err)
"

```
This mimics exactly how Airflow's DAG processor loads files and reports `import_errors` — the same mechanism that populates the "Import Errors" banner in the web UI. Useful for checking all DAGs in the folder at once, not just one file.

### 3. Against the running Docker stack (matches production behavior exactly)
If the docker-compose stack is already up:
```bash
cd /Users/wilsonwu/projects/terraform/se-data-eng-exercise/airflow
docker compose logs airflow-dag-processor | grep -A 20 my_old_dag
# or, using the airflow-cli debug profile:
docker compose run airflow-cli airflow dags list-import-errors
```
This confirms the exact error Airflow is logging in the running environment (Airflow 3.x parses DAGs in the dedicated `airflow-dag-processor` service, not the scheduler).

## Verification
Run option 1 first (fastest, no Docker needed) and confirm the traceback shows:
```
TypeError: BaseBranchOperator.__init__() missing 1 required positional argument: 'task_id'
```
This confirms the root cause identified earlier. Optionally also run option 2 to confirm Airflow's DagBag registers it under `import_errors` exactly as the web UI would show.
