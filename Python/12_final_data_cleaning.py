
import os
import pandas as pd

# =====================================================
# 1. PROJECT CONFIGURATION
# =====================================================

PROJECT_PATH = r"F:\Manjeet\DA Projects\AirScope"

INPUT_FILE = os.path.join(
    PROJECT_PATH,
    "Dataset", "Raw",
    "all_cities_january_2024_pilot.csv"
)

OUTPUT_FOLDER = os.path.join(
    PROJECT_PATH,
    "Dataset", "Cleaned"
)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

CLEAN_FILE = os.path.join(
    OUTPUT_FOLDER,
    "airscope_january_2024_cleaned.csv"
)

DUPLICATE_FILE = os.path.join(
    OUTPUT_FOLDER,
    "duplicate_records_review.csv"
)

INVALID_FILE = os.path.join(
    OUTPUT_FOLDER,
    "invalid_records_review.csv"
)

REPORT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "data_cleaning_report.csv"
)

TOLERANCE = 0.000001

# =====================================================
# 2. LOAD DATA
# =====================================================

print("\nLoading AirScope dataset...")

df = pd.read_csv(INPUT_FILE)

original_rows = len(df)

print("Original rows:", original_rows)

# =====================================================
# 3. STANDARDISE COLUMN NAMES
# =====================================================

df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

# =====================================================
# 4. DATA TYPE CONVERSION
# =====================================================

df["station_id"] = df["station_id"].astype("string")

df["period_start"] = pd.to_datetime(
    df["period_start"],
    errors="coerce"
)

numeric_columns = [
    "mean",
    "min",
    "max",
    "n",
    "latitude",
    "longitude"
]

for col in numeric_columns:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

# Standardise text fields
text_columns = [
    "parameter_name",
    "unit",
    "selected_city",
    "station_name",
    "city_name",
    "state_name",
    "source"
]

for col in text_columns:
    df[col] = df[col].astype("string").str.strip()

# =====================================================
# 5. MISSING VALUE VALIDATION
# =====================================================

required_columns = [
    "station_id",
    "parameter_name",
    "period_start",
    "mean",
    "min",
    "max",
    "n",
    "selected_city"
]

missing_rows = df[
    df[required_columns].isna().any(axis=1)
].copy()

print("\nRows with missing required values:",
      len(missing_rows))

# =====================================================
# 6. DUPLICATE VALIDATION
# =====================================================

duplicate_mask = df.duplicated(
    subset=[
        "station_id",
        "parameter_name",
        "period_start"
    ],
    keep="first"
)

duplicate_records = df[duplicate_mask].copy()

duplicate_records.to_csv(
    DUPLICATE_FILE,
    index=False
)

print("Duplicate records:", len(duplicate_records))

# =====================================================
# 7. INVALID MEASUREMENT VALIDATION
# =====================================================

invalid_mean_range = (
    (df["mean"] < df["min"] - TOLERANCE) |
    (df["mean"] > df["max"] + TOLERANCE)
)

invalid_negative = (
    (df["mean"] < 0) |
    (df["min"] < 0) |
    (df["max"] < 0)
)

invalid_observations = df["n"] <= 0

invalid_min_max = df["min"] > df["max"]

invalid_records = df[
    invalid_mean_range |
    invalid_negative |
    invalid_observations |
    invalid_min_max
].copy()

invalid_records.to_csv(
    INVALID_FILE,
    index=False
)

print("Invalid measurement records:",
      len(invalid_records))

# =====================================================
# 8. DATE AND POLLUTANT VALIDATION
# =====================================================

invalid_dates = df[
    df["period_start"].isna() |
    (df["period_start"] < "2024-01-01") |
    (df["period_start"] >= "2024-02-01")
]

invalid_pollutants = df[
    ~df["parameter_name"].isin(["PM2.5", "PM10"])
]

# =====================================================
# 9. CREATE CLEAN DATASET
# =====================================================

# Remove only confirmed duplicate records.
# Retain other records for investigation and transparency.

clean_df = df.loc[~duplicate_mask].copy()

# Add date attributes for future analysis
clean_df["year"] = clean_df["period_start"].dt.year
clean_df["month"] = clean_df["period_start"].dt.month
clean_df["month_name"] = (
    clean_df["period_start"].dt.strftime("%B")
)
clean_df["day"] = clean_df["period_start"].dt.day
clean_df["day_name"] = (
    clean_df["period_start"].dt.strftime("%A")
)

# Sort final data
clean_df = clean_df.sort_values(
    [
        "selected_city",
        "station_id",
        "parameter_name",
        "period_start"
    ]
).reset_index(drop=True)

# =====================================================
# 10. SAVE CLEAN DATASET
# =====================================================

clean_df.to_csv(
    CLEAN_FILE,
    index=False
)

# =====================================================
# 11. CLEANING REPORT
# =====================================================

report = pd.DataFrame([
    {
        "check": "Original records",
        "count": original_rows,
        "action": "Source dataset retained"
    },
    {
        "check": "Missing required value rows",
        "count": len(missing_rows),
        "action": "Reported; not silently removed"
    },
    {
        "check": "Duplicate records",
        "count": len(duplicate_records),
        "action": "Duplicates excluded from clean dataset"
    },
    {
        "check": "Invalid measurement records",
        "count": len(invalid_records),
        "action": "Flagged for review; retained"
    },
    {
        "check": "Invalid date records",
        "count": len(invalid_dates),
        "action": "Flagged for review; retained"
    },
    {
        "check": "Unexpected pollutant records",
        "count": len(invalid_pollutants),
        "action": "Flagged for review; retained"
    },
    {
        "check": "Final cleaned records",
        "count": len(clean_df),
        "action": "Saved"
    }
])

report.to_csv(
    REPORT_FILE,
    index=False
)

# =====================================================
# 12. FINAL SUMMARY
# =====================================================

print("\n" + "=" * 60)
print("AIRSCOPE DATA CLEANING SUMMARY")
print("=" * 60)

print("Original rows:", original_rows)
print("Final rows:", len(clean_df))
print("Rows removed as duplicates:",
      len(duplicate_records))

print("Missing required value rows:",
      len(missing_rows))

print("Invalid measurement records:",
      len(invalid_records))

print("Invalid date records:",
      len(invalid_dates))

print("Unexpected pollutant records:",
      len(invalid_pollutants))

print("Unique stations:",
      clean_df["station_id"].nunique())

print("Unique cities:",
      clean_df["selected_city"].nunique())

print("\nPollutant distribution:")
print(clean_df["parameter_name"].value_counts())

print("\nCity-wise record distribution:")
print(clean_df["selected_city"].value_counts())

print("\nOutput files:")
print(CLEAN_FILE)
print(DUPLICATE_FILE)
print(INVALID_FILE)
print(REPORT_FILE)

print("\nScript 12 completed successfully.")
