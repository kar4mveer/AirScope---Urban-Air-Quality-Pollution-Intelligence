
import os
import pandas as pd

# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_PATH = r"F:\Manjeet\DA Projects\AirScope"

INPUT_FILE = os.path.join(
    PROJECT_PATH,
    "Dataset",
    "Cleaned",
    "Historical_Final",
    "airscope_historical_2022_2024_cleaned.csv"
)

OUTPUT_FOLDER = os.path.join(
    PROJECT_PATH,
    "Dataset",
    "Cleaned",
    "Historical_Final",
    "SQL_Ready"
)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

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
    "historical_sql_export_validation.csv"
)

SUMMARY_FILE = os.path.join(
    OUTPUT_FOLDER,
    "historical_sql_export_summary.csv"
)

# ============================================================
# 2. LOAD CLEANED DATASET
# ============================================================

print("=" * 70)
print("AIRSCOPE - HISTORICAL SQL-READY EXPORT")
print("=" * 70)

if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError(
        f"Input file not found: {INPUT_FILE}"
    )

data = pd.read_csv(
    INPUT_FILE,
    dtype={"station_id": str}
)

print("\nCleaned dataset loaded.")
print("Total records:", len(data))

# ============================================================
# 3. VALIDATE INPUT STRUCTURE
# ============================================================

required_columns = [
    "station_id",
    "station_name",
    "selected_city",
    "parameter_name",
    "unit",
    "period_start",
    "mean",
    "min",
    "max",
    "n",
    "is_statistical_outlier"
]

missing_columns = [
    col for col in required_columns
    if col not in data.columns
]

if missing_columns:
    raise ValueError(
        f"Missing input columns: {missing_columns}"
    )

# ============================================================
# 4. STANDARDISE DATA TYPES
# ============================================================

print("\nStandardising data types...")

data["station_id"] = (
    data["station_id"].astype(str).str.strip()
)

data["station_name"] = (
    data["station_name"].astype(str).str.strip()
)

data["selected_city"] = (
    data["selected_city"].astype(str).str.strip()
)

data["parameter_name"] = (
    data["parameter_name"].astype(str).str.strip()
)

data["unit"] = (
    data["unit"].astype(str).str.strip()
)

data["period_start"] = pd.to_datetime(
    data["period_start"],
    errors="coerce"
)

for col in ["mean", "min", "max", "n"]:
    data[col] = pd.to_numeric(
        data[col],
        errors="coerce"
    )

# Parse the outlier flag safely
def to_boolean(value):

    return str(value).strip().lower() in [
        "true", "1", "yes"
    ]

data["is_statistical_outlier"] = (
    data["is_statistical_outlier"].apply(to_boolean)
)

if data[required_columns].isnull().any().any():
    raise ValueError(
        "Missing values found in required columns."
    )

# ============================================================
# 5. CREATE STATION DIMENSION
# ============================================================

print("\nCreating station dimension...")

station_dimension = (
    data[
        [
            "station_id",
            "station_name",
            "selected_city"
        ]
    ]
    .drop_duplicates()
    .sort_values(
        ["selected_city", "station_name", "station_id"]
    )
    .reset_index(drop=True)
)

# A station ID should map to one station name and city
station_mapping_check = (
    station_dimension.groupby("station_id")
    .agg(
        station_names=("station_name", "nunique"),
        cities=("selected_city", "nunique")
    )
)

if (
    (station_mapping_check["station_names"] > 1).any() or
    (station_mapping_check["cities"] > 1).any()
):
    raise ValueError(
        "A station ID maps to multiple names or cities. "
        "Review station metadata before exporting."
    )

station_dimension = (
    station_dimension
    .drop_duplicates(subset=["station_id"])
    .sort_values(
        ["selected_city", "station_name", "station_id"]
    )
    .reset_index(drop=True)
)

station_dimension.insert(
    0,
    "station_key",
    range(1, len(station_dimension) + 1)
)

station_dimension = station_dimension[
    [
        "station_key",
        "station_id",
        "station_name",
        "selected_city"
    ]
]

# ============================================================
# 6. CREATE DATE DIMENSION
# ============================================================

print("\nCreating date dimension...")

date_range = pd.date_range(
    start="2022-01-01",
    end="2024-12-31",
    freq="D"
)

date_dimension = pd.DataFrame({
    "date": date_range
})

date_dimension["date_key"] = (
    date_dimension["date"].dt.strftime("%Y%m%d").astype(int)
)

date_dimension["year"] = (
    date_dimension["date"].dt.year
)

date_dimension["quarter"] = (
    date_dimension["date"].dt.quarter
)

date_dimension["month_number"] = (
    date_dimension["date"].dt.month
)

date_dimension["month_name"] = (
    date_dimension["date"].dt.month_name()
)

date_dimension["year_month"] = (
    date_dimension["date"].dt.to_period("M").astype(str)
)

date_dimension["day_of_month"] = (
    date_dimension["date"].dt.day
)

# Monday = 1, Sunday = 7
date_dimension["day_of_week"] = (
    date_dimension["date"].dt.day_of_week + 1
)

date_dimension["day_name"] = (
    date_dimension["date"].dt.day_name()
)

date_dimension["is_weekend"] = (
    date_dimension["date"].dt.day_of_week >= 5
)

date_dimension = date_dimension[
    [
        "date_key",
        "date",
        "year",
        "quarter",
        "month_number",
        "month_name",
        "year_month",
        "day_of_month",
        "day_of_week",
        "day_name",
        "is_weekend"
    ]
]

# ============================================================
# 7. CREATE POLLUTANT DIMENSION
# ============================================================

print("\nCreating pollutant dimension...")

pollutant_dimension = (
    data[
        ["parameter_name", "unit"]
    ]
    .drop_duplicates()
    .sort_values("parameter_name")
    .reset_index(drop=True)
)

if pollutant_dimension["parameter_name"].duplicated().any():
    raise ValueError(
        "A pollutant maps to multiple units. "
        "Review pollutant metadata."
    )

pollutant_dimension.insert(
    0,
    "pollutant_key",
    range(1, len(pollutant_dimension) + 1)
)

pollutant_dimension = pollutant_dimension.rename(
    columns={
        "parameter_name": "pollutant_name"
    }
)

# ============================================================
# 8. CREATE FACT TABLE
# ============================================================

print("\nCreating fact table...")

fact = data.merge(
    station_dimension[
        ["station_key", "station_id"]
    ],
    on="station_id",
    how="left",
    validate="many_to_one"
)

fact = fact.merge(
    date_dimension[
        ["date_key", "date"]
    ],
    left_on="period_start",
    right_on="date",
    how="left",
    validate="many_to_one"
)

fact = fact.merge(
    pollutant_dimension[
        ["pollutant_key", "pollutant_name"]
    ],
    left_on="parameter_name",
    right_on="pollutant_name",
    how="left",
    validate="many_to_one"
)

fact = fact[
    [
        "station_key",
        "date_key",
        "pollutant_key",
        "mean",
        "min",
        "max",
        "n",
        "is_statistical_outlier"
    ]
].copy()

fact = fact.sort_values(
    [
        "station_key",
        "date_key",
        "pollutant_key"
    ]
).reset_index(drop=True)

# ============================================================
# 9. CREATE VALIDATION REPORT
# ============================================================

print("\nValidating SQL-ready tables...")

checks = []

def add_check(name, actual, expected):

    checks.append({
        "validation_check": name,
        "actual_result": actual,
        "expected_result": expected,
        "status": (
            "PASS"
            if actual == expected
            else "FAIL"
        )
    })

# Row count
add_check(
    "Fact table row count",
    len(fact),
    len(data)
)

# Dimension uniqueness
add_check(
    "Station dimension uniqueness",
    station_dimension["station_key"].nunique(),
    len(station_dimension)
)

add_check(
    "Station ID uniqueness",
    station_dimension["station_id"].nunique(),
    len(station_dimension)
)

add_check(
    "Date dimension uniqueness",
    date_dimension["date_key"].nunique(),
    len(date_dimension)
)

add_check(
    "Pollutant dimension uniqueness",
    pollutant_dimension["pollutant_key"].nunique(),
    len(pollutant_dimension)
)

# Foreign keys
station_key_errors = (
    fact["station_key"].isna().sum()
)

date_key_errors = (
    fact["date_key"].isna().sum()
)

pollutant_key_errors = (
    fact["pollutant_key"].isna().sum()
)

add_check(
    "Station foreign key errors",
    int(station_key_errors),
    0
)

add_check(
    "Date foreign key errors",
    int(date_key_errors),
    0
)

add_check(
    "Pollutant foreign key errors",
    int(pollutant_key_errors),
    0
)

# Fact grain uniqueness
fact_duplicates = fact.duplicated(
    subset=[
        "station_key",
        "date_key",
        "pollutant_key"
    ]
).sum()

add_check(
    "Fact table grain uniqueness",
    int(fact_duplicates),
    0
)

# Null keys
null_keys = fact[
    [
        "station_key",
        "date_key",
        "pollutant_key"
    ]
].isnull().sum().sum()

add_check(
    "Null fact table keys",
    int(null_keys),
    0
)

# Measurement value preservation
add_check(
    "PM2.5 record count",
    int((data["parameter_name"] == "PM2.5").sum()),
    int((fact["pollutant_key"] == pollutant_dimension.loc[
        pollutant_dimension["pollutant_name"] == "PM2.5",
        "pollutant_key"
    ].iloc[0]).sum())
)

add_check(
    "PM10 record count",
    int((data["parameter_name"] == "PM10").sum()),
    int((fact["pollutant_key"] == pollutant_dimension.loc[
        pollutant_dimension["pollutant_name"] == "PM10",
        "pollutant_key"
    ].iloc[0]).sum())
)

validation_report = pd.DataFrame(checks)

# ============================================================
# 10. SAVE SQL-READY CSV FILES
# ============================================================

print("\nSaving SQL-ready tables...")

if (validation_report["status"] != "PASS").any():

    print("\nValidation failed. Files will not be exported.")

    print(
        validation_report.to_string(index=False)
    )

    raise ValueError(
        "Resolve failed validation checks before export."
    )

fact.to_csv(
    FACT_FILE,
    index=False
)

station_dimension.to_csv(
    STATION_FILE,
    index=False
)

date_dimension.to_csv(
    DATE_FILE,
    index=False
)

pollutant_dimension.to_csv(
    POLLUTANT_FILE,
    index=False
)

validation_report.to_csv(
    VALIDATION_FILE,
    index=False
)

# ============================================================
# 11. CREATE EXPORT SUMMARY
# ============================================================

summary = pd.DataFrame([{

    "fact_records": len(fact),
    "unique_stations": len(station_dimension),
    "date_dimension_records": len(date_dimension),
    "pollutant_dimension_records": len(pollutant_dimension),
    "pm25_records": int(
        (data["parameter_name"] == "PM2.5").sum()
    ),
    "pm10_records": int(
        (data["parameter_name"] == "PM10").sum()
    ),
    "statistical_outlier_records": int(
        fact["is_statistical_outlier"].sum()
    ),
    "validation_checks_passed": int(
        (validation_report["status"] == "PASS").sum()
    ),
    "validation_checks_failed": int(
        (validation_report["status"] == "FAIL").sum()
    )

}])

summary.to_csv(
    SUMMARY_FILE,
    index=False
)

# ============================================================
# 12. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("AIRSCOPE - HISTORICAL SQL-READY EXPORT SUMMARY")
print("=" * 70)

print("Fact table rows:", len(fact))
print("Unique stations:", len(station_dimension))
print("Date dimension rows:", len(date_dimension))
print("Pollutant dimension rows:", len(pollutant_dimension))

print(
    "PM2.5 records:",
    int((data["parameter_name"] == "PM2.5").sum())
)

print(
    "PM10 records:",
    int((data["parameter_name"] == "PM10").sum())
)

print(
    "Statistical outlier flags:",
    int(fact["is_statistical_outlier"].sum())
)

print("\nValidation results:")
print(validation_report.to_string(index=False))

print(
    "\nPassed checks:",
    (validation_report["status"] == "PASS").sum()
)

print(
    "Failed checks:",
    (validation_report["status"] == "FAIL").sum()
)

print("\nOutput files:")
print(FACT_FILE)
print(STATION_FILE)
print(DATE_FILE)
print(POLLUTANT_FILE)
print(VALIDATION_FILE)
print(SUMMARY_FILE)

print("\nScript 20 completed.")
