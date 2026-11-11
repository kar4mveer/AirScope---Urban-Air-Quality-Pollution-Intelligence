
import os
import pandas as pd

# ============================================================
# 1. CONFIGURATION
# ============================================================

PROJECT_PATH = r"F:\Manjeet\DA Projects\AirScope"

BASE_FOLDER = os.path.join(
    PROJECT_PATH,
    "Dataset",
    "Raw",
    "Historical_2022_2024"
)

STATION_FOLDER = os.path.join(
    BASE_FOLDER,
    "Station_Month_Files"
)

LOG_FILE = os.path.join(
    BASE_FOLDER,
    "extraction_log.csv"
)

OUTPUT_FOLDER = os.path.join(
    PROJECT_PATH,
    "Dataset",
    "Cleaned"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "airscope_historical_2022_2024_combined.csv"
)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ============================================================
# 2. LOAD EXTRACTION LOG
# ============================================================

print("=" * 65)
print("AIRSCOPE - HISTORICAL DATA COMBINATION")
print("=" * 65)

log_df = pd.read_csv(
    LOG_FILE,
    dtype={"station_id": str}
)

successful_log = log_df[
    log_df["status"] == "success"
].copy()

print("\nSuccessful extraction files expected:",
      len(successful_log))

# ============================================================
# 3. LOAD AND COMBINE FILES
# ============================================================

all_data = []
missing_files = []
failed_files = []

for index, row in successful_log.iterrows():

    station_id = str(row["station_id"])
    month = str(row["month"])

    filename = f"{station_id}_{month}.csv"

    file_path = os.path.join(
        STATION_FOLDER,
        filename
    )

    if not os.path.exists(file_path):

        missing_files.append(filename)
        continue

    try:

        df = pd.read_csv(file_path)

        if df.empty:
            continue

        df["station_id"] = (
            df["station_id"].astype(str)
        )

        df["period_start"] = pd.to_datetime(
            df["period_start"],
            errors="coerce"
        )

        df["selected_city"] = row["selected_city"]
        df["station_name"] = row["station_name"]

        all_data.append(df)

    except Exception as error:

        failed_files.append({
            "filename": filename,
            "error": str(error)
        })

    if (index + 1) % 250 == 0:

        print(
            "Processed log entries:",
            index + 1,
            "/",
            len(successful_log)
        )

if not all_data:

    raise ValueError(
        "No historical measurement files could be combined."
    )

combined = pd.concat(
    all_data,
    ignore_index=True
)

print("\nAll files combined.")

# ============================================================
# 4. STANDARDIZE COLUMN ORDER
# ============================================================

combined["year"] = (
    combined["period_start"].dt.year
)

combined["year_month"] = (
    combined["period_start"].dt.to_period("M").astype(str)
)

column_order = [
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

combined = combined[column_order]

# Sort records
combined = combined.sort_values(
    by=[
        "selected_city",
        "station_id",
        "period_start",
        "parameter_name"
    ]
).reset_index(drop=True)

# ============================================================
# 5. VALIDATE COMBINED DATASET
# ============================================================

print("\nValidating combined dataset...")

actual_records = len(combined)

expected_records = int(
    successful_log["records"].sum()
)

unique_stations = combined["station_id"].nunique()

unique_cities = combined["selected_city"].nunique()

unique_pollutants = combined["parameter_name"].nunique()

duplicate_records = combined.duplicated(
    subset=[
        "station_id",
        "parameter_name",
        "period_start"
    ]
).sum()

missing_values = combined[
    column_order
].isnull().sum().sum()

# ============================================================
# 6. CREATE VALIDATION REPORT
# ============================================================

checks = [

    {
        "validation_check": "Combined record count",
        "actual_result": actual_records,
        "expected_result": expected_records,
        "status": (
            "PASS"
            if actual_records == expected_records
            else "FAIL"
        )
    },

    {
        "validation_check": "Unique stations",
        "actual_result": unique_stations,
        "expected_result": 109,
        "status": (
            "PASS"
            if unique_stations == 109
            else "REVIEW"
        )
    },

    {
        "validation_check": "Unique cities",
        "actual_result": unique_cities,
        "expected_result": 6,
        "status": (
            "PASS"
            if unique_cities == 6
            else "FAIL"
        )
    },

    {
        "validation_check": "Unique pollutants",
        "actual_result": unique_pollutants,
        "expected_result": 2,
        "status": (
            "PASS"
            if unique_pollutants == 2
            else "FAIL"
        )
    },

    {
        "validation_check": "Duplicate records",
        "actual_result": int(duplicate_records),
        "expected_result": 0,
        "status": (
            "PASS"
            if duplicate_records == 0
            else "FAIL"
        )
    },

    {
        "validation_check": "Missing values",
        "actual_result": int(missing_values),
        "expected_result": 0,
        "status": (
            "PASS"
            if missing_values == 0
            else "FAIL"
        )
    }

]

validation_report = pd.DataFrame(checks)

validation_report.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "historical_combination_validation.csv"
    ),
    index=False
)

# ============================================================
# 7. SAVE COMBINED DATASET
# ============================================================

if (
    missing_files or
    failed_files or
    actual_records != expected_records
):

    print("\nWARNING: Combination issues detected.")
    print("Combined file will not be saved as final.")

else:

    combined.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\nCombined dataset saved successfully.")

# ============================================================
# 8. SAVE FILE ISSUE REPORTS
# ============================================================

pd.DataFrame(
    {"missing_file": missing_files}
).to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "combination_missing_files.csv"
    ),
    index=False
)

pd.DataFrame(
    failed_files,
    columns=["filename", "error"]
).to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "combination_failed_files.csv"
    ),
    index=False
)

# ============================================================
# 9. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 65)
print("AIRSCOPE - COMBINED DATASET SUMMARY")
print("=" * 65)

print("Expected records:", expected_records)
print("Combined records:", actual_records)
print("Unique stations:", unique_stations)
print("Unique cities:", unique_cities)
print("Unique pollutants:", unique_pollutants)
print("Duplicate records:", duplicate_records)
print("Missing values:", missing_values)

print("Missing files:", len(missing_files))
print("Failed files:", len(failed_files))

print("\nYear-wise records:")
print(
    combined.groupby("year").size().to_string()
)

print("\nCity-wise records:")
print(
    combined.groupby("selected_city").size().to_string()
)

print("\nPollutant-wise records:")
print(
    combined.groupby("parameter_name").size().to_string()
)

print("\nValidation report:")
print(validation_report.to_string(index=False))

print("\nOutput file:")
print(OUTPUT_FILE)

print("\nScript 18 completed.")
