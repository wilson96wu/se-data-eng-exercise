# Create `taxi_trips_raw` Table in Snowflake Raw Layer via Terraform

## Context

The team needs the `taxi_trips_raw` table (Snowflake, `EE_SE_DE_DB` database, per-user schema) to exist as version-controlled infrastructure rather than a manually-run DDL script, so the structure is reproducible across environments and reviewable in git — same pattern already used for the GCS bucket and BigQuery dataset in this repo (`terraform/main.tf`, `terraform/bigquery.tf`). All columns must be strings (VARCHAR) except `created_timestamp`, which is a real `TIMESTAMP_NTZ` defaulting to `CURRENT_TIMESTAMP()` — this is deliberate so malformed source data never fails ingestion on a type mismatch; only the load-time audit column gets a real type.

Today the repo has **no Snowflake provider, credentials, or resources at all** (confirmed via full-repo search) — this is a from-scratch addition on top of the existing flat `terraform/` root module (`main.tf`, `providers.tf`, `versions.tf`, `variables.tf`, `bigquery.tf`, `service_account.tf`, `outputs.tf`, all local state, no `terraform.tfvars`).

**Decisions confirmed with the user:**
- Auth method: a **Snowflake CLI connection profile** (`~/.snowflake/config`), not variables/tfvars or shell env vars — keeps every credential (account, user, role, warehouse, private key path) out of the Terraform files entirely. The provider block only references `profile = var.snowflake_profile`.
- Schema name: **`wilson`** (matches the existing per-user naming convention: `sa-data-landing-wilson`, `movies_data_wilson`).
- Account identifier: use `ipb17578.us-east-1` exactly as given in the ticket (legacy locator+region format) rather than splitting into `organization_name`/`account_name` — this is the standard SnowSQL/gosnowflake locator format and doesn't require a separate org name.

## Manual prerequisite (outside Terraform, one-time, per participant)

Before any `terraform apply` can authenticate, generate an RSA key pair and register the public key with Snowflake (this only works because the `SE_DE_PARTICIPANT` role was granted ownership of the user, per the ticket's prerequisite):

```bash
mkdir -p ~/.snowflake/keys
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out ~/.snowflake/keys/wilson_rsa_key.p8 -nocrypt
openssl rsa -in ~/.snowflake/keys/wilson_rsa_key.p8 -pubout -out ~/.snowflake/keys/wilson_rsa_key.pub
chmod 600 ~/.snowflake/keys/wilson_rsa_key.p8
```

In a Snowflake worksheet (logged in as the participant user, using `SE_DE_PARTICIPANT` role):
```sql
ALTER USER <username> SET RSA_PUBLIC_KEY='<contents of wilson_rsa_key.pub, header/footer lines stripped>';
```

Create `~/.snowflake/config` (TOML, modern field names) with a profile the provider will reference:
```toml
[wilson]
account_name    = "ipb17578.us-east-1"
user            = "<username>"
authenticator   = "SNOWFLAKE_JWT"
private_key_path = "/Users/wilson/.snowflake/keys/wilson_rsa_key.p8"
role            = "SE_DE_PARTICIPANT"
warehouse       = "EE_TEST"
```
This file lives outside the repo (`~/.snowflake/config`), so no gitignore changes are needed for secrets.

*Note: if `terraform init`/`plan` reports an account-resolution error with this locator format, the fallback is to add `organization_name` to the profile — flag this back if it happens, since we don't have the org name confirmed.*

## Terraform changes

**`terraform/versions.tf`** — add the Snowflake provider to `required_providers`:
```hcl
snowflake = {
  source  = "snowflakedb/snowflake"
  version = "~> 2.0"
}
```

**`terraform/providers.tf`** — add a minimal provider block that only points at the CLI profile:
```hcl
provider "snowflake" {
  profile = var.snowflake_profile
}
```

**`terraform/variables.tf`** — add:
```hcl
variable "snowflake_profile" {
  description = "Name of the connection profile in ~/.snowflake/config to authenticate with"
  type        = string
  default     = "wilson"
}

variable "snowflake_database" {
  description = "Snowflake database for the raw layer"
  type        = string
  default     = "EE_SE_DE_DB"
}

variable "snowflake_schema_name" {
  description = "Per-user Snowflake schema for the raw layer"
  type        = string
  default     = "wilson"
}
```

**New file `terraform/snowflake_taxi_trips.tf`** — schema + table, following the `bigquery.tf` style (labels/comment, `delete_contents_on_destroy`-equivalent safety where available):

```hcl
resource "snowflake_schema" "wilson" {
  database = var.snowflake_database
  name     = var.snowflake_schema_name
  comment  = "Raw layer schema for wilson"
}

resource "snowflake_table" "taxi_trips_raw" {
  database = snowflake_schema.wilson.database
  schema   = snowflake_schema.wilson.name
  name     = "taxi_trips_raw"
  comment  = "Raw layer taxi trips table — all source columns kept as strings except the load timestamp, so malformed data never fails ingestion on a type mismatch."

  column { name = "VendorId"               type = "VARCHAR" }
  column { name = "tpep_pickup_datetime"    type = "VARCHAR" }
  column { name = "tpep_dropoff_datetime"   type = "VARCHAR" }
  column { name = "passenger_count"         type = "VARCHAR" }
  column { name = "trip_distance"           type = "VARCHAR" }
  column { name = "pickup_longitude"        type = "VARCHAR" }
  column { name = "pickup_latitude"         type = "VARCHAR" }
  column { name = "RatecodeID"              type = "VARCHAR" }
  column { name = "store_and_fwd_flag"      type = "VARCHAR" }
  column { name = "dropoff_longitude"       type = "VARCHAR" }
  column { name = "dropoff_latitude"        type = "VARCHAR" }
  column { name = "payment_type"            type = "VARCHAR" }
  column { name = "fare_amount"             type = "VARCHAR" }
  column { name = "extra"                   type = "VARCHAR" }
  column { name = "mta_tax"                 type = "VARCHAR" }
  column { name = "tip_amount"              type = "VARCHAR" }
  column { name = "tolls_amount"            type = "VARCHAR" }
  column { name = "improvement_surcharge"   type = "VARCHAR" }
  column { name = "total_amount"            type = "VARCHAR" }
  column { name = "trip_duration_minutes"   type = "VARCHAR" }
  column { name = "trip_speed_mph"          type = "VARCHAR" }

  column {
    name = "created_timestamp"
    type = "TIMESTAMP_NTZ"
    default {
      expression = "CURRENT_TIMESTAMP()"
    }
  }
}
```

**`terraform/outputs.tf`** — add for easy verification after apply:
```hcl
output "snowflake_schema_name" {
  value = snowflake_schema.wilson.name
}

output "snowflake_taxi_trips_raw_fqn" {
  value = "${snowflake_table.taxi_trips_raw.database}.${snowflake_table.taxi_trips_raw.schema}.${snowflake_table.taxi_trips_raw.name}"
}
```

## Deploy & verify

1. `cd terraform && terraform init` — pulls the `snowflakedb/snowflake` provider (updates `.terraform.lock.hcl`).
2. `terraform plan` — review that it shows creating `snowflake_schema.wilson` and `snowflake_table.taxi_trips_raw` only (no unrelated diffs to the existing GCP resources).
3. `terraform apply`.
4. Verify in Snowflake (Snowsight or SnowSQL, role `SE_DE_PARTICIPANT`):
   ```sql
   USE DATABASE EE_SE_DE_DB;
   DESC TABLE wilson.taxi_trips_raw;
   ```
   Confirm all 21 source columns show `VARCHAR`/`TEXT` and `created_timestamp` shows `TIMESTAMP_NTZ` with default `CURRENT_TIMESTAMP()`.
5. `terraform output` to confirm `snowflake_taxi_trips_raw_fqn` prints `EE_SE_DE_DB.wilson.taxi_trips_raw`.
