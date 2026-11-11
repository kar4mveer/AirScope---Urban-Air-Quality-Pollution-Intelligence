
import os
import pandas as pd
import numpy as np

# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_PATH = r"F:\Manjeet\DA Projects\AirScope"

INPUT_FILE = os.path.join(
    PROJECT_PATH,
    "Dataset",
    "Cleaned",
    "airscope_historical_2022_2024_combined.csv"
)

OUTPUT_FOLDER = os.path.join(
    PROJECT_PATH,
    "Dataset",
    "Cleaned",
    "Historical_Final"
)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

CLEAN_FILE = os.path.join(
    OUTPUT_FOLDER,
    "airscope_historical_2022_2024_cleaned.csv"
)

INVALID_FILE = os.path.join(
    OUTPUT_FOLDER,
    "invalid_records_review.csv"
)

DUPLICATE_FILE = os.path.join(
    OUTPUT_FOLDER,
    "duplicate_records_review.csv"
)

OUTLIER_FILE = os.path.join(
    OUTPUT_FOLDER,
    "statistical_outlier_review.csv"
)

QUALITY_FILE = os.path.join(
    OUTPUT_FOLDER,
    "historical_cleaning_quality_report.csv"
)

SUMMARY_FILE = os.path.join(
    OUTPUT_FOLDER,
    "historical_cleaning_summary.csv"
)

# ============================================================
# 2. LOAD COMBINED DATASET
# ============================================================

print("=" * 70)
print("AIRSCOPE - HISTORICAL DATA CLEANING")
print("=" * 70)

if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError(
        f"Input file not found: {INPUT_FILE}"
    )

data = pd.read_csv(
    INPUT_FILE,
    dtype={"station_id": str}
)

original_count = len(data)

print("\nDataset loaded successfully.")
print("Original records:", original_count)

# ============================================================
# 3. CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "station_id",
    "station_name",
    "selected_city",
    "parameter_name",
    "unit",
    "period_start",
    "year",
    "year_month",
    "mean",
    "min",
    "max",
    "n"
]

missing_columns = [
    col for col in required_columns
    if col not in data.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )

# ============================================================
# 4. STANDARDISE TEXT COLUMNS
# ============================================================

print("\nStandardising text columns...")

text_columns = [
    "station_id",
    "station_name",
    "selected_city",
    "parameter_name",
    "unit"
]

for col in text_columns:

    data[col] = (
        data[col]
        .astype("string")
        .str.strip()
    )

# Standardise city names and pollutant labels
data["selected_city"] = (
    data["selected_city"].str.title()
)

data["parameter_name"] = (
    data["parameter_name"].str.upper()
    .replace({
        "PM2.5": "PM2.5",
        "PM10": "PM10"
    })
)

# ============================================================
# 5. CONVERT DATA TYPES
# ============================================================

print("\nConverting data types...")

data["period_start"] = pd.to_datetime(
    data["period_start"],
    errors="coerce"
)

numeric_columns = [
    "mean",
    "min",
    "max",
    "n",
    "year"
]

for col in numeric_columns:

    data[col] = pd.to_numeric(
        data[col],
        errors="coerce"
    )

# Rebuild year and year_month from the date
valid_date_mask = data["period_start"].notna()

data.loc[valid_date_mask, "year"] = (
    data.loc[valid_date_mask, "period_start"].dt.year
)

data["year_month"] = (
    data["period_start"]
    .dt.to_period("M")
    .astype("string")
)

# ============================================================
# 6. CHECK MISSING VALUES
# ============================================================

print("\nChecking missing values...")

missing_report = (
    data[required_columns]
    .isna()
    .sum()
    .reset_index()
)

missing_report.columns = [
    "column",
    "missing_count"
]

print(missing_report.to_string(index=False))

# ============================================================
# 7. CHECK INVALID RECORDS
# ============================================================

print("\nChecking invalid measurements...")

required_value_columns = [
    "station_id",
    "station_name",
    "selected_city",
    "parameter_name",
    "unit",
    "period_start",
    "mean",
    "min",
    "max",
    "n"
]

missing_required_mask = (
    data[required_value_columns].isna().any(axis=1)
)

allowed_pollutants = ["PM2.5", "PM10"]

unexpected_pollutant_mask = (
    ~data["parameter_name"].isin(allowed_pollutants)
)

invalid_date_mask = (
    data["period_start"].isna() |
    (data["period_start"] < pd.Timestamp("2022-01-01")) |
    (data["period_start"] > pd.Timestamp("2024-12-31"))
)

negative_measurement_mask = (
    (data["mean"] < 0) |
    (data["min"] < 0) |
    (data["max"] < 0)
)

invalid_observation_count_mask = (
    data["n"].isna() |
    (data["n"] <= 0)
)

invalid_range_mask = (
    (data["min"] > data["max"]) |
    (data["mean"] < data["min"] - 0.000001) |
    (data["mean"] > data["max"] + 0.000001)
)

invalid_mask = (
    missing_required_mask |
    unexpected_pollutant_mask |
    invalid_date_mask |
    negative_measurement_mask |
    invalid_observation_count_mask |
    invalid_range_mask
)

invalid_records = data[invalid_mask].copy()

invalid_records.to_csv(
    INVALID_FILE,
    index=False
)

print("Missing required fields:", int(missing_required_mask.sum()))
print("Unexpected pollutants:", int(unexpected_pollutant_mask.sum()))
print("Invalid dates:", int(invalid_date_mask.sum()))
print("Negative measurements:", int(negative_measurement_mask.sum()))
print("Invalid observation counts:", int(invalid_observation_count_mask.sum()))
print("Invalid measurement ranges:", int(invalid_range_mask.sum()))
print("Total invalid records:", len(invalid_records))

# ============================================================
# 8. CHECK DUPLICATE RECORDS
# ============================================================

print("\nChecking duplicate records...")

duplicate_mask = data.duplicated(
    subset=[
        "station_id",
        "parameter_name",
        "period_start"
    ],
    keep="first"
)

duplicate_records = data[
    duplicate_mask
].copy()

duplicate_records.to_csv(
    DUPLICATE_FILE,
    index=False
)

print("Duplicate records:", len(duplicate_records))

# ============================================================
# 9. CREATE VALID CLEANING BASE
# ============================================================

print("\nCreating validated dataset...")

# Exclude invalid records and subsequent duplicate copies.
# All excluded records are preserved in separate review files.

clean_mask = (
    ~invalid_mask &
    ~duplicate_mask
)

cleaned = data[clean_mask].copy()

cleaned = cleaned.sort_values(
    by=[
        "selected_city",
        "station_id",
        "period_start",
        "parameter_name"
    ]
).reset_index(drop=True)

print("Records before cleaning:", original_count)
print("Records after cleaning:", len(cleaned))
print("Records excluded:", original_count - len(cleaned))

# ============================================================
# 10. STATISTICAL OUTLIER ANALYSIS
# ============================================================

print("\nCreating statistical outlier flags...")

# IQR method applied separately to each pollutant.
# Outliers are flagged, NOT removed.

outlier_frames = []

for pollutant in allowed_pollutants:

    pollutant_data = cleaned[
        cleaned["parameter_name"] == pollutant
    ].copy()

    if pollutant_data.empty:
        continue

    q1 = pollutant_data["mean"].quantile(0.25)
    q3 = pollutant_data["mean"].quantile(0.75)

    iqr = q3 - q1

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    pollutant_data["iqr_lower_bound"] = lower_bound
    pollutant_data["iqr_upper_bound"] = upper_bound

    pollutant_data["is_iqr_outlier"] = (
        (pollutant_data["mean"] < lower_bound) |
        (pollutant_data["mean"] > upper_bound)
    )

    outlier_frames.append(
        pollutant_data[
            pollutant_data["is_iqr_outlier"]
        ]
    )

if outlier_frames:

    outliers = pd.concat(
        outlier_frames,
        ignore_index=True
    )

else:

    outliers = pd.DataFrame()

outliers.to_csv(
    OUTLIER_FILE,
    index=False
)

# Add outlier flag to the cleaned dataset
cleaned["is_statistical_outlier"] = False

if not outliers.empty:

    outlier_keys = set(
        zip(
            outliers["station_id"],
            outliers["parameter_name"],
            outliers["period_start"]
        )
    )

    cleaned["is_statistical_outlier"] = [
        (
            station,
            pollutant,
            date
        ) in outlier_keys

        for station, pollutant, date in zip(
            cleaned["station_id"],
            cleaned["parameter_name"],
            cleaned["period_start"]
        )
    ]

print("Statistical outliers:", len(outliers))

print("\nOutlier count by pollutant:")

if not outliers.empty:

    print(
        outliers["parameter_name"]
        .value_counts()
        .to_string()
    )

# ============================================================
# 11. FINAL DATASET VALIDATION
# ============================================================

print("\nPerforming final validation...")

final_duplicates = cleaned.duplicated(
    subset=[
        "station_id",
        "parameter_name",
        "period_start"
    ]
).sum()

final_missing_values = cleaned[
    required_value_columns
].isna().sum().sum()

final_invalid_values = (
    (cleaned["mean"] < 0) |
    (cleaned["min"] < 0) |
    (cleaned["max"] < 0) |
    (cleaned["n"] <= 0) |
    (cleaned["min"] > cleaned["max"]) |
    (cleaned["mean"] < cleaned["min"] - 0.000001) |
    (cleaned["mean"] > cleaned["max"] + 0.000001)
).sum()

final_unexpected_pollutants = (
    ~cleaned["parameter_name"].isin(allowed_pollutants)
).sum()

final_invalid_dates = (
    cleaned["period_start"].isna() |
    (cleaned["period_start"] < pd.Timestamp("2022-01-01")) |
    (cleaned["period_start"] > pd.Timestamp("2024-12-31"))
).sum()

# ============================================================
# 12. VALIDATION REPORT
# ============================================================

checks = [

    {
        "validation_check": "Original record count",
        "actual_result": original_count,
        "expected_result": 198259,
        "status": "PASS" if original_count == 198259 else "REVIEW"
    },

    {
        "validation_check": "Cleaned record count",
        "actual_result": len(cleaned),
        "expected_result": original_count,
        "status": "PASS" if len(cleaned) == original_count else "REVIEW"
    },

    {
        "validation_check": "Missing required values",
        "actual_result": int(final_missing_values),
        "expected_result": 0,
        "status": "PASS" if final_missing_values == 0 else "FAIL"
    },

    {
        "validation_check": "Duplicate records",
        "actual_result": int(final_duplicates),
        "expected_result": 0,
        "status": "PASS" if final_duplicates == 0 else "FAIL"
    },

    {
        "validation_check": "Invalid measurements",
        "actual_result": int(final_invalid_values),
        "expected_result": 0,
        "status": "PASS" if final_invalid_values == 0 else "FAIL"
    },

    {
        "validation_check": "Unexpected pollutants",
        "actual_result": int(final_unexpected_pollutants),
        "expected_result": 0,
        "status": "PASS" if final_unexpected_pollutants == 0 else "FAIL"
    },

    {
        "validation_check": "Invalid dates",
        "actual_result": int(final_invalid_dates),
        "expected_result": 0,
        "status": "PASS" if final_invalid_dates == 0 else "FAIL"
    },

    {
        "validation_check": "Statistical outliers removed",
        "actual_result": 0,
        "expected_result": 0,
        "status": "PASS"
    }

]

validation_report = pd.DataFrame(checks)

validation_report.to_csv(
    QUALITY_FILE,
    index=False
)

# ============================================================
# 13. CITY AND POLLUTANT SUMMARY
# ============================================================

print("\nGenerating city-pollutant summary...")

city_summary = (
    cleaned.groupby([
        "selected_city",
        "parameter_name"
    ])
    .agg(
        measurement_records=("mean", "count"),
        reporting_stations=("station_id", "nunique"),
        average_daily_mean=("mean", "mean"),
        minimum_value=("min", "min"),
        maximum_value=("max", "max"),
        total_observations=("n", "sum"),
        statistical_outliers=("is_statistical_outlier", "sum")
    )
    .reset_index()
)

city_summary.to_csv(
    SUMMARY_FILE,
    index=False
)

# ============================================================
# 14. SAVE FINAL CLEANED DATASET
# ============================================================

cleaned.to_csv(
    CLEAN_FILE,
    index=False
)

# ============================================================
# 15. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("AIRSCOPE - HISTORICAL CLEANING SUMMARY")
print("=" * 70)

print("Original records:", original_count)
print("Cleaned records:", len(cleaned))
print("Excluded records:", original_count - len(cleaned))

print(
    "Unique stations:",
    cleaned["station_id"].nunique()
)

print(
    "Unique cities:",
    cleaned["selected_city"].nunique()
)

print(
    "PM2.5 records:",
    (cleaned["parameter_name"] == "PM2.5").sum()
)

print(
    "PM10 records:",
    (cleaned["parameter_name"] == "PM10").sum()
)

print("Duplicate records:", final_duplicates)
print("Missing values:", final_missing_values)
print("Invalid measurements:", final_invalid_values)
print("Statistical outliers flagged:", len(outliers))

print("\nCity-pollutant summary:")
print(city_summary.to_string(index=False))

print("\nFinal validation report:")
print(validation_report.to_string(index=False))

print("\nOutput files:")
print("Clean dataset:", CLEAN_FILE)
print("Invalid records:", INVALID_FILE)
print("Duplicate records:", DUPLICATE_FILE)
print("Outlier review:", OUTLIER_FILE)
print("Quality report:", QUALITY_FILE)
print("City summary:", SUMMARY_FILE)

print("\nScript 19 completed.")
