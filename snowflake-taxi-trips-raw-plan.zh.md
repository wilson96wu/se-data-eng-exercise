# 通过 Terraform 在 Snowflake 原始层创建 `taxi_trips_raw` 表

## 背景

团队需要 `taxi_trips_raw` 表（Snowflake，数据库 `EE_SE_DE_DB`，按用户区分的 schema）以版本控制的基础设施代码形式存在，而不是手工运行的 DDL 脚本，这样表结构在各环境中都可复现、可在 git 中审阅——与本仓库中 GCS bucket 和 BigQuery dataset 已经采用的模式一致（`terraform/main.tf`、`terraform/bigquery.tf`）。除 `created_timestamp` 外，所有列都必须是字符串（VARCHAR）；`created_timestamp` 是真正的 `TIMESTAMP_NTZ` 类型，默认值为 `CURRENT_TIMESTAMP()`——这是刻意设计的，目的是让格式错误的源数据不会因类型不匹配而导致写入失败；只有这个记录加载时间的审计列才使用真实类型。

目前仓库中**完全没有 Snowflake provider、凭据或相关资源**（已通过全仓库搜索确认)——这是在现有的扁平化 `terraform/` 根模块之上从零新增的内容（`main.tf`、`providers.tf`、`versions.tf`、`variables.tf`、`bigquery.tf`、`service_account.tf`、`outputs.tf`，均为本地 state，没有 `terraform.tfvars`）。

**已与用户确认的决定：**
- 认证方式：使用 **Snowflake CLI 连接配置文件**（`~/.snowflake/config`），而不是变量/tfvars 或 shell 环境变量——这样所有凭据（account、user、role、warehouse、私钥路径）都完全不出现在 Terraform 文件中。provider 代码块只需引用 `profile = var.snowflake_profile`。
- Schema 名称：**`wilson`**（与仓库中已有的按用户命名惯例一致：`sa-data-landing-wilson`、`movies_data_wilson`）。
- Account 标识符：**已核实并修正**——经查看 Snowsight 中的真实账户详情，ticket 里给出的 `ipb17578.us-east-1` 其实只是旧版的账户 *locator*（已确认：`IPB17578` 对应 Snowsight 中的 "Account locator" 字段），并不是现代 provider 可以直接使用的标识符。真正应使用的值是 `organization_name = "GUSDATD"` 和 `account_name = "DAB70621"`（分别来自 Snowsight 的 "Organization name" / "Account name" 字段）——这两个才是 provider 的主要、非实验性字段，因此不再需要 locator/region 的后备方案。登录名（`user` 字段）为 `WILSONWU`。
- Warehouse：**已核实并修正**——ticket 里给的 `EE_TEST` 在账户里并不存在（`USE ROLE SE_DE_PARTICIPANT; SHOW WAREHOUSES;` 只返回一个 `SNOWFLAKE_LEARNING_WH`），实际连接时应使用 `SNOWFLAKE_LEARNING_WH`。
- Database：**已核实并修正**——ticket 里给的 `EE_SE_DE_DB` 在账户里同样不存在（`SHOW DATABASES` 未列出该库）。角色 `SE_DE_PARTICIPANT` 实际拥有所有权（owner）的数据库是 `NEW_YORK_311`，这才是应该使用的值。

## 手动前置步骤（在 Terraform 之外，每位参与者一次性操作）

在 `terraform apply` 能够完成认证之前，需要生成一对 RSA 密钥并将公钥注册到 Snowflake（这一步之所以可行，是因为 `SE_DE_PARTICIPANT` 角色已被授予该用户的 ownership，正如 ticket 前置条件所述）：

```bash
mkdir -p ~/.snowflake/keys
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out ~/.snowflake/keys/wilson_rsa_key.p8 -nocrypt
openssl rsa -in ~/.snowflake/keys/wilson_rsa_key.p8 -pubout -out ~/.snowflake/keys/wilson_rsa_key.pub
chmod 600 ~/.snowflake/keys/wilson_rsa_key.p8
```

在 Snowflake worksheet 中（以参与者本人账号登录，使用 `SE_DE_PARTICIPANT` 角色）：
```sql
ALTER USER WILSONWU SET RSA_PUBLIC_KEY='<wilson_rsa_key.pub 的内容，去掉首尾的 header/footer 行>';
```

创建 `~/.snowflake/config`（TOML 格式，使用现代字段名），provider 将引用其中的配置项：
```toml
[wilson]
organization_name = "GUSDATD"
account_name      = "DAB70621"
user              = "WILSONWU"
authenticator     = "SNOWFLAKE_JWT"
private_key       = '''-----BEGIN PRIVATE KEY-----
<wilson_rsa_key.p8 的完整内容，包含 header/footer 行>
-----END PRIVATE KEY-----'''
role              = "SE_DE_PARTICIPANT"
warehouse         = "SNOWFLAKE_LEARNING_WH"
```
该文件位于仓库之外（`~/.snowflake/config`），因此无需为保护密钥而修改 `.gitignore`。

**重要（部署时发现）：** provider v2 的 TOML 配置**不支持** `private_key_path` 字段——即使写了也会被静默忽略，导致 `terraform apply` 报错 `trying to use keypair authentication, but PrivateKey was not provided in the driver config`。必须把私钥文件的**完整内容**直接内嵌到 `private_key` 字段里（用 TOML 三引号 `'''...'''` 保留换行），而不是引用文件路径。

另外，`~/.snowflake/config` 文件本身也必须设置为所有者独占权限，否则 provider 会拒绝加载并报 `unsafe permissions - 0644`：
```bash
chmod 600 ~/.snowflake/config
```

## Terraform 变更内容

**`terraform/versions.tf`** —— 在 `required_providers` 中新增 Snowflake provider：
```hcl
snowflake = {
  source  = "snowflakedb/snowflake"
  version = "~> 2.0"
}
```

**`terraform/providers.tf`** —— 新增一个仅指向 CLI 配置文件的最简 provider 代码块：
```hcl
provider "snowflake" {
  profile                  = var.snowflake_profile
  preview_features_enabled = ["snowflake_table_resource"]
}
```
**部署时发现：** `snowflake_table` 资源目前是 provider 的预览特性（preview feature），不加 `preview_features_enabled` 会导致 `terraform apply` 直接报错拒绝执行。

**`terraform/variables.tf`** —— 新增：
```hcl
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
```

**新文件 `terraform/snowflake_taxi_trips.tf`** —— schema 与表资源，风格参照 `bigquery.tf`（注释/comment，以及在可用的情况下类似 `delete_contents_on_destroy` 的安全设置）：

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

**`terraform/outputs.tf`** —— 新增便于部署后验证的输出：
```hcl
output "snowflake_schema_name" {
  value = snowflake_schema.wilson.name
}

output "snowflake_taxi_trips_raw_fqn" {
  value = "${snowflake_table.taxi_trips_raw.database}.${snowflake_table.taxi_trips_raw.schema}.${snowflake_table.taxi_trips_raw.name}"
}
```

## 部署与验证

1. `cd terraform && terraform init` —— 拉取 `snowflakedb/snowflake` provider（会更新 `.terraform.lock.hcl`）。
2. `terraform plan` —— 检查计划中只会创建 `snowflake_schema.wilson` 和 `snowflake_table.taxi_trips_raw`（不应对现有的 GCP 资源产生额外变更）。
3. `terraform apply`。
4. 在 Snowflake 中验证（Snowsight 或 SnowSQL，角色为 `SE_DE_PARTICIPANT`）：
   ```sql
   USE DATABASE NEW_YORK_311;
   DESC TABLE wilson.taxi_trips_raw;
   ```
   确认全部源列都显示为 `VARCHAR`/`TEXT`，且 `created_timestamp` 显示为 `TIMESTAMP_NTZ`，默认值为 `CURRENT_TIMESTAMP()`。
5. 执行 `terraform output`，确认 `snowflake_taxi_trips_raw_fqn` 输出为 `NEW_YORK_311.wilson.taxi_trips_raw`。

**部署时发现的坑（大小写/引号）：** Terraform provider 建表时会给标识符加双引号，保留 `.tf` 文件里写的原始大小写（`wilson`、`taxi_trips_raw` 都是小写）。因此在 Snowflake 里查询时，如果不加引号直接写 `SELECT * FROM taxi_trips_raw`，Snowflake 会自动把它转成大写 `TAXI_TRIPS_RAW` 去匹配，从而报 "does not exist or not authorized"。查询时需要给表名/schema 名加双引号保留小写：
```sql
SELECT * FROM NEW_YORK_311."wilson"."taxi_trips_raw" LIMIT 100;
```

## 部署过程中发现并修正的其他问题

- **`snowflake_taxi_trips.tf` 里 `passenger_count` 列被重复定义了两次**，导致 `terraform apply` 报 `duplicate column name 'passenger_count'`。已删除多余的一份。
- **`terraform/service_account.tf` 中 `google_service_account.airflow_gcs` 的 `account_id = "airflow-gcs-sa"` 与共享 GCP 项目 `ee-sa-se-data` 中已存在的同名资源冲突**（报 `409 alreadyExists`），推断是其他参与者或早期版本遗留的资源。此问题与本文档的 Snowflake 表主题无关，但发生在同一次 `terraform apply` 里，修复方式是仿照仓库里其他资源的命名惯例加上 `wilson` 后缀：`account_id = "airflow-gcs-sa-wilson"`。
- 部署所用的 GCP 账户 (`gcloud config set account ...`) 和项目 (`gcloud config set project ee-sa-se-data`) 需要与 `wilson96wu@gmail.com` 匹配才能通过权限校验；同时 `gcloud auth application-default login` 也需要用同一账户重新登录，否则会报 `oauth2: "invalid_grant" "invalid_rapt"`。
