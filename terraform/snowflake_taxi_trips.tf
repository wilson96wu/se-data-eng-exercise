resource "snowflake_schema" "wilson" {
  database = var.snowflake_database
  name     = var.snowflake_schema_name
  comment  = "Raw layer schema for wilson"
}


resource "snowflake_table" "taxi_trips_raw" {
  database = snowflake_schema.wilson.database
  schema   = snowflake_schema.wilson.name
  name     = "taxi_trips_raw"
  comment  = "Raw layer taxi trips table - all source columns kept as strings expcept the load timestamp, so malformed data never fails ingestion on a type mismatch"

  column {
    name = "VendorId"
    type = "VARCHAR"
  }

  column {
    name = "tpep_pickup_datetime"
    type = "VARCHAR"
  }

  column {
    name = "tpep_dropoff_datetime"
    type = "VARCHAR"
  }

  column {
    name = "passenger_count"
    type = "VARCHAR"
  }

  column {
    name = "pickup_longitude"
    type = "VARCHAR"
  }

  column {
    name = "pickup_latitude"
    type = "VARCHAR"
  }

  column {
    name = "RatecodeID"
    type = "VARCHAR"
  }

  column {
    name = "store_and_fwd_flag"
    type = "VARCHAR"
  }

  column {
    name = "dropoff_longitude"
    type = "VARCHAR"
  }

  column {
    name = "dropoff_latitude"
    type = "VARCHAR"
  }

  column {
    name = "payment_type"
    type = "VARCHAR"
  }

  column {
    name = "fare_amount"
    type = "VARCHAR"
  }

  column {
    name = "extra"
    type = "VARCHAR"
  }

  column {
    name = "mta_tax"
    type = "VARCHAR"
  }

  column {
    name = "tip_amount"
    type = "VARCHAR"
  }

  column {
    name = "tolls_amount"
    type = "VARCHAR"
  }

  column {
    name = "improvement_surcharge"
    type = "VARCHAR"
  }

  column {
    name = "total_amount"
    type = "VARCHAR"
  }

  column {
    name = "trip_duration_minutes"
    type = "VARCHAR"
  }

  column {
    name = "trip_speed_mph"
    type = "VARCHAR"
  }

  column {
    name = "created_timestamp"
    type = "TIMESTAMP_NTZ"
    default {
      expression = "CURRENT_TIMESTAMP()"
    }
  }
}
