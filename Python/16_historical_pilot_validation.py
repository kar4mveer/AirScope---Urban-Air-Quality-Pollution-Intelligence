
import os
import glob
import pandas as pd

# ============================================================
# 1. PROJECT CONFIGURATION
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
    "Raw",
    "Historical_2022_2024",
    "January_2022_Validation"
)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Analysis period
START_DATE = pd.Timestamp("2022-01-01")
END_DATE = pd.Timestamp("2022-01-31")

EXPECTED_DAYS = pd.date_range(
    START_DATE,
    END_DATE,
    freq="D"
)

EXPECTED_POLLUTANTS = [
    "PM2.5",
    "PM10"
]

# ============================================================
# 2. LOAD EXTRACTION LOG
# ============================================================

print("=" * 65)
print("AIRSCOPE - JANUARY 2022 PILOT VALIDATION")
print("=" * 65)

if not os.path.exists(LOG_FILE):
    raise FileNotFoundError(
        "Extraction log not found."
    )

log_df = pd.read_csv(
    LOG_FILE,
    dtype={"station_id": str}
)

print("\nExtraction log loaded.")
print("Logged tasks:", len(log_df))

# ============================================================
# 3. LOAD SUCCESSFUL STATION FILES
# ============================================================

print("\nLoading station-month files...")

successful_log = log_df[
    log_df["status"] == "success"
].copy()

all_data = []

file_errors = []

for _, row in successful_log.iterrows():

    station_id = str(row["station_id"])
    month = str(row["month"])

    file_path = os.path.join(
        STATION_FOLDER,
        f"{station_id}_{month}.csv"
    )

    if not os.path.exists(file_path):

        file_errors.append({
            "station_id": station_id,
            "month": month,
            "issue": "Successful log entry but file missing"
        })

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

        file_errors.append({
            "station_id": station_id,
            "month": month,
            "issue": str(error)
        })

if not all_data:

    raise ValueError(
        "No measurement data could be loaded."
    )

data = pd.concat(
    all_data,
    ignore_index=True
)

print("Total loaded records:", len(data))

# ============================================================
# 4. CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "station_id",
    "parameter_name",
    "unit",
    "period_start",
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
# 5. DATA TYPE CONVERSION
# ============================================================

for col in ["mean", "min", "max", "n"]:

    data[col] = pd.to_numeric(
        data[col],
        errors="coerce"
    )

data["parameter_name"] = (
    data["parameter_name"].astype(str).str.strip()
)

# ============================================================
# 6. BASIC DATA SUMMARY
# ============================================================

print("\nBasic data summary")
print("-" * 45)

print("Total records:", len(data))

print(
    "Unique stations:",
    data["station_id"].nunique()
)

print(
    "Unique cities:",
    data["selected_city"].nunique()
)

print(
    "Unique pollutants:",
    data["parameter_name"].nunique()
)

print(
    "Date range:",
    data["period_start"].min(),
    "to",
    data["period_start"].max()
)

print("\nPollutant record counts:")

print(
    data["parameter_name"].value_counts().to_string()
)

# ============================================================
# 7. CHECK MISSING VALUES
# ============================================================

print("\nChecking missing values...")

required_check_columns = [
    "station_id",
    "parameter_name",
    "period_start",
    "mean",
    "min",
    "max",
    "n"
]

missing_summary = (
    data[required_check_columns]
    .isnull()
    .sum()
    .reset_index()
)

missing_summary.columns = [
    "column",
    "missing_count"
]

missing_summary.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "missing_values_report.csv"
    ),
    index=False
)

print(missing_summary.to_string(index=False))

# ============================================================
# 8. DUPLICATE RECORD CHECK
# ============================================================

print("\nChecking duplicate records...")

duplicate_mask = data.duplicated(
    subset=[
        "station_id",
        "parameter_name",
        "period_start"
    ],
    keep=False
)

duplicates = data[
    duplicate_mask
].copy()

duplicates.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "duplicate_records.csv"
    ),
    index=False
)

print("Duplicate records:", len(duplicates))

# ============================================================
# 9. INVALID MEASUREMENT CHECK
# ============================================================

print("\nChecking invalid measurements...")

invalid_negative = (
    (data["mean"] < 0) |
    (data["min"] < 0) |
    (data["max"] < 0)
)

invalid_n = data["n"] <= 0

invalid_range = (
    (data["min"] > data["max"]) |
    (data["mean"] < data["min"] - 0.000001) |
    (data["mean"] > data["max"] + 0.000001)
)

invalid_dates = (
    data["period_start"].isna() |
    (data["period_start"] < START_DATE) |
    (data["period_start"] > END_DATE)
)

unexpected_pollutants = ~data[
    "parameter_name"
].isin(EXPECTED_POLLUTANTS)

invalid_mask = (
    invalid_negative |
    invalid_n |
    invalid_range |
    invalid_dates |
    unexpected_pollutants
)

invalid_records = data[
    invalid_mask
].copy()

invalid_records.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "invalid_measurements.csv"
    ),
    index=False
)

print("Negative measurements:", int(invalid_negative.sum()))
print("Invalid observation counts:", int(invalid_n.sum()))
print("Invalid measurement ranges:", int(invalid_range.sum()))
print("Invalid dates:", int(invalid_dates.sum()))
print("Unexpected pollutants:", int(unexpected_pollutants.sum()))
print("Total flagged records:", len(invalid_records))

# ============================================================
# 10. STATION-POLLUTANT COVERAGE
# ============================================================

print("\nCalculating station-pollutant coverage...")

coverage = (
    data.groupby([
        "selected_city",
        "station_id",
        "station_name",
        "parameter_name"
    ])
    .agg(
        records=("period_start", "count"),
        unique_days=("period_start", "nunique"),
        total_observations=("n", "sum"),
        first_date=("period_start", "min"),
        last_date=("period_start", "max"),
        average_mean=("mean", "mean"),
        minimum_value=("min", "min"),
        maximum_value=("max", "max")
    )
    .reset_index()
)

coverage["missing_days"] = (
    len(EXPECTED_DAYS) - coverage["unique_days"]
)

coverage["coverage_percentage"] = (
    coverage["unique_days"] /
    len(EXPECTED_DAYS) * 100
)

coverage["coverage_status"] = (
    coverage["unique_days"].apply(
        lambda x: "Complete"
        if x == len(EXPECTED_DAYS)
        else "Incomplete"
    )
)

coverage.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "station_pollutant_coverage.csv"
    ),
    index=False
)

print("\nStation-pollutant coverage:")
print(
    coverage["coverage_status"].value_counts().to_string()
)

# ============================================================
# 11. MISSING DAILY RECORDS
# ============================================================

print("\nIdentifying missing daily records...")

missing_daily = []

for _, row in coverage.iterrows():

    station_id = row["station_id"]
    pollutant = row["parameter_name"]

    observed_dates = set(
        data.loc[
            (data["station_id"] == station_id) &
            (data["parameter_name"] == pollutant),
            "period_start"
        ].dt.normalize().dropna()
    )

    for date in EXPECTED_DAYS:

        if date not in observed_dates:

            missing_daily.append({

                "selected_city": row["selected_city"],
                "station_id": station_id,
                "station_name": row["station_name"],
                "parameter_name": pollutant,
                "missing_date": date.strftime("%Y-%m-%d")

            })

missing_daily_df = pd.DataFrame(
    missing_daily,
    columns=[
        "selected_city",
        "station_id",
        "station_name",
        "parameter_name",
        "missing_date"
    ]
)

missing_daily_df.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "missing_daily_records.csv"
    ),
    index=False
)

print("Missing daily records:", len(missing_daily_df))

# ============================================================
# 12. CITY-WISE POLLUTANT COVERAGE
# ============================================================

print("\nCalculating city-wise coverage...")

city_coverage = (
    coverage.groupby([
        "selected_city",
        "parameter_name"
    ])
    .agg(
        stations_reporting=("station_id", "nunique"),
        total_daily_records=("records", "sum"),
        complete_station_count=(
            "coverage_status",
            lambda x: (x == "Complete").sum()
        ),
        incomplete_station_count=(
            "coverage_status",
            lambda x: (x == "Incomplete").sum()
        ),
        average_station_coverage=(
            "coverage_percentage",
            "mean"
        )
    )
    .reset_index()
)

city_coverage.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "city_pollutant_coverage.csv"
    ),
    index=False
)

print(city_coverage.to_string(index=False))

# ============================================================
# 13. NO-DATA STATION REPORT
# ============================================================

print("\nCreating no-data station report...")

no_data_stations = log_df[
    log_df["status"] == "no_data"
].copy()

no_data_stations.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "no_data_stations.csv"
    ),
    index=False
)

print(
    "Stations with no data:",
    len(no_data_stations)
)

# ============================================================
# 14. FILE ERROR REPORT
# ============================================================

file_errors_df = pd.DataFrame(
    file_errors,
    columns=[
        "station_id",
        "month",
        "issue"
    ]
)

file_errors_df.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "file_errors.csv"
    ),
    index=False
)

# ============================================================
# 15. VALIDATION CHECKLIST
# ============================================================

print("\nCreating validation checklist...")

checks = [

    {
        "validation_check": "Loaded measurement records",
        "actual_result": len(data),
        "expected_result": 4838,
        "status": "PASS" if len(data) == 4838 else "REVIEW"
    },

    {
        "validation_check": "Unique stations",
        "actual_result": data["station_id"].nunique(),
        "expected_result": 80,
        "status": "PASS" if data["station_id"].nunique() == 80 else "REVIEW"
    },

    {
        "validation_check": "Missing required values",
        "actual_result": int(data[required_check_columns].isnull().sum().sum()),
        "expected_result": 0,
        "status": "PASS" if data[required_check_columns].isnull().sum().sum() == 0 else "FAIL"
    },

    {
        "validation_check": "Duplicate records",
        "actual_result": len(duplicates),
        "expected_result": 0,
        "status": "PASS" if len(duplicates) == 0 else "FAIL"
    },

    {
        "validation_check": "Invalid measurements",
        "actual_result": len(invalid_records),
        "expected_result": 0,
        "status": "PASS" if len(invalid_records) == 0 else "FAIL"
    },

    {
        "validation_check": "Missing daily records",
        "actual_result": len(missing_daily_df),
        "expected_result": 0,
        "status": "REVIEW" if len(missing_daily_df) > 0 else "PASS"
    }

]

validation_report = pd.DataFrame(checks)

validation_report.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "historical_pilot_validation_report.csv"
    ),
    index=False
)

# ============================================================
# 16. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 65)
print("AIRSCOPE - JANUARY 2022 VALIDATION SUMMARY")
print("=" * 65)

print("Total records:", len(data))

print(
    "Unique stations:",
    data["station_id"].nunique()
)

print(
    "Unique cities:",
    data["selected_city"].nunique()
)

print(
    "PM2.5 records:",
    (data["parameter_name"] == "PM2.5").sum()
)

print(
    "PM10 records:",
    (data["parameter_name"] == "PM10").sum()
)

print(
    "Duplicate records:",
    len(duplicates)
)

print(
    "Invalid records:",
    len(invalid_records)
)

print(
    "Missing daily records:",
    len(missing_daily_df)
)

print(
    "No-data station tasks:",
    len(no_data_stations)
)

print("\nValidation checklist:")
print(validation_report.to_string(index=False))

print("\nOutput folder:")
print(OUTPUT_FOLDER)

print("\nScript 16 completed.")
 
