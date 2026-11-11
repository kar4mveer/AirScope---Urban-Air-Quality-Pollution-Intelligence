
import os
import pandas as pd

# =====================================================
# 1. PROJECT CONFIGURATION
# =====================================================

PROJECT_PATH = r"F:\Manjeet\DA Projects\AirScope"

INPUT_FILE = os.path.join(
    PROJECT_PATH,
    "Dataset", "Cleaned",
    "airscope_january_2024_cleaned.csv"
)

OUTPUT_FOLDER = os.path.join(
    PROJECT_PATH,
    "Dataset", "Cleaned", "SQL_Ready"
)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Output files
FACT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "fact_air_quality_daily.csv"
)

STATION_FILE = os.path.join(
    OUTPUT_FOLDER,
    "dim_station.csv"
)

DATE_FILE = os.path.join(
    OUTPUT_FOLDER,
    "dim_date.csv"
)

POLLUTANT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "dim_pollutant.csv"
)

VALIDATION_FILE = os.path.join(
    OUTPUT_FOLDER,
    "sql_export_validation_report.csv"
)

# =====================================================
# 2. LOAD CLEANED DATASET
# =====================================================

print("\nLoading cleaned AirScope dataset...")

df = pd.read_csv(INPUT_FILE)

df["period_start"] = pd.to_datetime(
    df["period_start"],
    errors="coerce"
)

print("Total records:", len(df))

# =====================================================
# 3. CREATE ANOMALY FLAGS
# =====================================================

print("\nCreating anomaly flags...")

df["statistical_outlier_flag"] = False

for pollutant in df["parameter_name"].dropna().unique():

    mask = df["parameter_name"] == pollutant

    values = df.loc[mask, "mean"]

    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)

    iqr = q3 - q1

    lower_limit = q1 - (1.5 * iqr)
    upper_limit = q3 + (1.5 * iqr)

    df.loc[mask, "statistical_outlier_flag"] = (
        (values < lower_limit) |
        (values > upper_limit)
    )

# Investigation threshold used in Script 13A
df["extreme_value_flag"] = (
    (df["mean"] >= 300) |
    (df["max"] >= 900)
)

# Precision-aware measurement validation
tolerance = 0.000001

df["range_validation_flag"] = (
    (df["mean"] >= df["min"] - tolerance) &
    (df["mean"] <= df["max"] + tolerance)
)

# =====================================================
# 4. CREATE DIMENSION TABLES
# =====================================================

print("\nCreating dimension tables...")

# ------------------------------
# DIMENSION 1: STATION
# ------------------------------

station_columns = [
    "station_id",
    "station_name",
    "city_name",
    "selected_city",
    "state_name",
    "source",
    "latitude",
    "longitude"
]

dim_station = (
    df[station_columns]
    .drop_duplicates(subset=["station_id"])
    .sort_values("station_id")
    .reset_index(drop=True)
)

dim_station.to_csv(
    STATION_FILE,
    index=False
)

# ------------------------------
# DIMENSION 2: DATE
# ------------------------------

dates = (
    df["period_start"]
    .dropna()
    .drop_duplicates()
    .sort_values()
)

dim_date = pd.DataFrame({
    "date_key": dates.dt.strftime("%Y%m%d").astype(int),
    "full_date": dates.dt.strftime("%Y-%m-%d"),
    "year": dates.dt.year,
    "quarter": dates.dt.quarter,
    "month": dates.dt.month,
    "month_name": dates.dt.strftime("%B"),
    "day": dates.dt.day,
    "day_name": dates.dt.strftime("%A"),
    "day_of_week": dates.dt.day_of_week + 1
})

dim_date = dim_date.reset_index(drop=True)

dim_date.to_csv(
    DATE_FILE,
    index=False
)

# ------------------------------
# DIMENSION 3: POLLUTANT
# ------------------------------

dim_pollutant = (
    df[["parameter_name", "unit"]]
    .drop_duplicates()
    .sort_values("parameter_name")
    .reset_index(drop=True)
)

dim_pollutant["pollutant_key"] = (
    range(1, len(dim_pollutant) + 1)
)

dim_pollutant = dim_pollutant[
    ["pollutant_key", "parameter_name", "unit"]
]

dim_pollutant.to_csv(
    POLLUTANT_FILE,
    index=False
)

# =====================================================
# 5. CREATE FACT TABLE
# =====================================================

print("\nCreating fact table...")

fact_columns = [
    "station_id",
    "period_start",
    "parameter_name",
    "mean",
    "min",
    "max",
    "n",
    "statistical_outlier_flag",
    "extreme_value_flag",
    "range_validation_flag"
]

fact = df[fact_columns].copy()

fact["date_key"] = (
    fact["period_start"].dt.strftime("%Y%m%d")
)

fact["date_key"] = pd.to_numeric(
    fact["date_key"],
    errors="coerce"
).astype("Int64")

# Map pollutant names to pollutant keys
pollutant_mapping = dict(
    zip(
        dim_pollutant["parameter_name"],
        dim_pollutant["pollutant_key"]
    )
)

fact["pollutant_key"] = (
    fact["parameter_name"].map(pollutant_mapping)
)

# Final fact table columns
fact = fact[
    [
        "station_id",
        "date_key",
        "pollutant_key",
        "mean",
        "min",
        "max",
        "n",
        "statistical_outlier_flag",
        "extreme_value_flag",
        "range_validation_flag"
    ]
].copy()

fact.to_csv(
    FACT_FILE,
    index=False
)

# =====================================================
# 6. VALIDATE TABLE RELATIONSHIPS
# =====================================================

print("\nValidating SQL-ready tables...")

checks = []

def add_check(name, actual, expected, status, details=""):
    checks.append({
        "validation_check": name,
        "actual_result": actual,
        "expected_result": expected,
        "status": status,
        "details": details
    })

# Fact row count
add_check(
    "Fact table row count",
    len(fact),
    len(df),
    "PASS" if len(fact) == len(df) else "FAIL"
)

# Unique station IDs
add_check(
    "Station dimension uniqueness",
    dim_station["station_id"].nunique(),
    len(dim_station),
    "PASS" if dim_station["station_id"].is_unique else "FAIL"
)

# Unique dates
add_check(
    "Date dimension uniqueness",
    dim_date["date_key"].nunique(),
    len(dim_date),
    "PASS" if dim_date["date_key"].is_unique else "FAIL"
)

# Unique pollutant keys
add_check(
    "Pollutant dimension uniqueness",
    dim_pollutant["pollutant_key"].nunique(),
    len(dim_pollutant),
    "PASS" if dim_pollutant["pollutant_key"].is_unique else "FAIL"
)

# Foreign key validation
invalid_station_keys = (
    ~fact["station_id"].isin(dim_station["station_id"])
).sum()

invalid_date_keys = (
    ~fact["date_key"].isin(dim_date["date_key"])
).sum()

invalid_pollutant_keys = (
    ~fact["pollutant_key"].isin(
        dim_pollutant["pollutant_key"]
    )
).sum()

add_check(
    "Station foreign keys",
    invalid_station_keys,
    0,
    "PASS" if invalid_station_keys == 0 else "FAIL"
)

add_check(
    "Date foreign keys",
    invalid_date_keys,
    0,
    "PASS" if invalid_date_keys == 0 else "FAIL"
)

add_check(
    "Pollutant foreign keys",
    invalid_pollutant_keys,
    0,
    "PASS" if invalid_pollutant_keys == 0 else "FAIL"
)

# Fact table grain uniqueness
fact_duplicates = fact.duplicated(
    subset=[
        "station_id",
        "date_key",
        "pollutant_key"
    ]
).sum()

add_check(
    "Fact table grain uniqueness",
    fact_duplicates,
    0,
    "PASS" if fact_duplicates == 0 else "FAIL"
)

# Null key checks
null_keys = fact[
    ["station_id", "date_key", "pollutant_key"]
].isna().any(axis=1).sum()

add_check(
    "Null fact table keys",
    null_keys,
    0,
    "PASS" if null_keys == 0 else "FAIL"
)

# =====================================================
# 7. SAVE VALIDATION REPORT
# =====================================================

validation_report = pd.DataFrame(checks)

validation_report.to_csv(
    VALIDATION_FILE,
    index=False
)

# =====================================================
# 8. FINAL SUMMARY
# =====================================================

print("\n" + "=" * 60)
print("AIRSCOPE SQL-READY EXPORT SUMMARY")
print("=" * 60)

print("Fact table rows:", len(fact))
print("Unique stations:", len(dim_station))
print("Unique dates:", len(dim_date))
print("Unique pollutants:", len(dim_pollutant))

print("\nValidation results:")
print(validation_report.to_string(index=False))

print("\nPassed checks:",
      (validation_report["status"] == "PASS").sum())

print("Failed checks:",
      (validation_report["status"] == "FAIL").sum())

print("\nOutput files:")
print(FACT_FILE)
print(STATION_FILE)
print(DATE_FILE)
print(POLLUTANT_FILE)
print(VALIDATION_FILE)

print("\nScript 14 completed.")
