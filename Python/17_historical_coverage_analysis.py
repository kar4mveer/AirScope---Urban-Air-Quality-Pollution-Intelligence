
import os
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
    BASE_FOLDER,
    "Historical_Coverage_Analysis"
)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

START_DATE = pd.Timestamp("2022-01-01")
END_DATE = pd.Timestamp("2024-12-31")

EXPECTED_POLLUTANTS = ["PM2.5", "PM10"]

# ============================================================
# 2. LOAD EXTRACTION LOG
# ============================================================

print("=" * 70)
print("AIRSCOPE - FULL HISTORICAL COVERAGE ANALYSIS")
print("=" * 70)

if not os.path.exists(LOG_FILE):
    raise FileNotFoundError("Extraction log not found.")

log_df = pd.read_csv(
    LOG_FILE,
    dtype={"station_id": str}
)

required_log_columns = [
    "station_id",
    "selected_city",
    "station_name",
    "month",
    "status",
    "records"
]

missing_log_columns = [
    col for col in required_log_columns
    if col not in log_df.columns
]

if missing_log_columns:
    raise ValueError(
        f"Missing log columns: {missing_log_columns}"
    )

log_df["month"] = log_df["month"].astype(str)

log_df["records"] = pd.to_numeric(
    log_df["records"],
    errors="coerce"
).fillna(0)

print("\nExtraction log loaded.")
print("Total logged tasks:", len(log_df))

print("\nExtraction status:")
print(log_df["status"].value_counts().to_string())

# ============================================================
# 3. CHECK LOG STRUCTURE
# ============================================================

print("\nChecking extraction log consistency...")

duplicate_log_tasks = log_df.duplicated(
    subset=["station_id", "month"],
    keep=False
)

duplicate_log_df = log_df[
    duplicate_log_tasks
].copy()

duplicate_log_df.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "duplicate_log_tasks.csv"
    ),
    index=False
)

print(
    "Duplicate station-month log entries:",
    len(duplicate_log_df)
)

if len(duplicate_log_df) > 0:
    raise ValueError(
        "Duplicate station-month entries found. "
        "Resolve the log before continuing."
    )

# ============================================================
# 4. LOAD SUCCESSFUL STATION-MONTH FILES
# ============================================================

print("\nLoading historical station-month files...")

successful_log = log_df[
    log_df["status"] == "success"
].copy()

all_data = []

file_issues = []

loaded_file_count = 0

for index, row in successful_log.iterrows():

    station_id = str(row["station_id"])
    month = str(row["month"])

    filename = f"{station_id}_{month}.csv"

    file_path = os.path.join(
        STATION_FOLDER,
        filename
    )

    if not os.path.exists(file_path):

        file_issues.append({
            "station_id": station_id,
            "month": month,
            "issue": "Successful log entry but file missing",
            "expected_records": row["records"],
            "actual_records": 0
        })

        continue

    try:

        df = pd.read_csv(file_path)

        actual_records = len(df)

        if actual_records != row["records"]:

            file_issues.append({
                "station_id": station_id,
                "month": month,
                "issue": "Log record count mismatch",
                "expected_records": row["records"],
                "actual_records": actual_records
            })

        if df.empty:
            continue

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
            if col not in df.columns
        ]

        if missing_columns:

            file_issues.append({
                "station_id": station_id,
                "month": month,
                "issue": (
                    "Missing columns: " +
                    ", ".join(missing_columns)
                ),
                "expected_records": row["records"],
                "actual_records": actual_records
            })

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
        df["source_month"] = month

        all_data.append(df)

        loaded_file_count += 1

    except Exception as error:

        file_issues.append({
            "station_id": station_id,
            "month": month,
            "issue": str(error),
            "expected_records": row["records"],
            "actual_records": 0
        })

    if (loaded_file_count % 250 == 0 and
            loaded_file_count > 0):

        print(
            "Files loaded:",
            loaded_file_count
        )

if not all_data:
    raise ValueError("No historical measurement files loaded.")

data = pd.concat(
    all_data,
    ignore_index=True
)

print("\nFiles successfully loaded:", loaded_file_count)
print("Total loaded records:", len(data))

# ============================================================
# 5. SAVE FILE ISSUE REPORT
# ============================================================

file_issues_df = pd.DataFrame(
    file_issues,
    columns=[
        "station_id",
        "month",
        "issue",
        "expected_records",
        "actual_records"
    ]
)

file_issues_df.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "file_issues_report.csv"
    ),
    index=False
)

# ============================================================
# 6. BASIC DATA SUMMARY
# ============================================================

print("\nBasic historical data summary")
print("-" * 50)

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
    "First date:",
    data["period_start"].min()
)

print(
    "Last date:",
    data["period_start"].max()
)

print("\nPollutant-wise record count:")

print(
    data["parameter_name"].value_counts().to_string()
)

print("\nCity-wise record count:")

print(
    data.groupby("selected_city").size().to_string()
)

# ============================================================
# 7. DATA TYPE CONVERSION
# ============================================================

for column in ["mean", "min", "max", "n"]:

    data[column] = pd.to_numeric(
        data[column],
        errors="coerce"
    )

data["parameter_name"] = (
    data["parameter_name"].astype(str).str.strip()
)

# ============================================================
# 8. MISSING VALUE CHECK
# ============================================================

print("\nChecking missing values...")

required_columns = [
    "station_id",
    "parameter_name",
    "period_start",
    "mean",
    "min",
    "max",
    "n"
]

missing_values = (
    data[required_columns]
    .isnull()
    .sum()
    .reset_index()
)

missing_values.columns = [
    "column",
    "missing_count"
]

missing_values.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "missing_values_report.csv"
    ),
    index=False
)

print(missing_values.to_string(index=False))

# ============================================================
# 9. DUPLICATE RECORD CHECK
# ============================================================

print("\nChecking duplicate measurement records...")

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
        "duplicate_measurements.csv"
    ),
    index=False
)

print("Duplicate records:", len(duplicates))

# ============================================================
# 10. INVALID MEASUREMENT CHECK
# ============================================================

print("\nChecking invalid measurements...")

negative_mask = (
    (data["mean"] < 0) |
    (data["min"] < 0) |
    (data["max"] < 0)
)

invalid_n_mask = data["n"] <= 0

invalid_range_mask = (
    (data["min"] > data["max"]) |
    (data["mean"] < data["min"] - 0.000001) |
    (data["mean"] > data["max"] + 0.000001)
)

invalid_date_mask = (
    data["period_start"].isna() |
    (data["period_start"] < START_DATE) |
    (data["period_start"] > END_DATE)
)

unexpected_pollutant_mask = ~data[
    "parameter_name"
].isin(EXPECTED_POLLUTANTS)

invalid_mask = (
    negative_mask |
    invalid_n_mask |
    invalid_range_mask |
    invalid_date_mask |
    unexpected_pollutant_mask
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

print("Negative measurements:", int(negative_mask.sum()))
print("Invalid observation counts:", int(invalid_n_mask.sum()))
print("Invalid ranges:", int(invalid_range_mask.sum()))
print("Invalid dates:", int(invalid_date_mask.sum()))
print("Unexpected pollutants:", int(unexpected_pollutant_mask.sum()))
print("Total flagged records:", len(invalid_records))

# ============================================================
# 11. LOG VS ACTUAL RECORD COUNT
# ============================================================

print("\nComparing extraction log with actual records...")

log_total = int(
    log_df.loc[
        log_df["status"] == "success",
        "records"
    ].sum()
)

actual_total = len(data)

record_comparison = pd.DataFrame([{
    "log_successful_tasks": len(successful_log),
    "loaded_files": loaded_file_count,
    "log_expected_records": log_total,
    "actual_loaded_records": actual_total,
    "difference": actual_total - log_total,
    "status": (
        "PASS"
        if actual_total == log_total
        else "REVIEW"
    )
}])

record_comparison.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "log_vs_actual_record_comparison.csv"
    ),
    index=False
)

print(record_comparison.to_string(index=False))

# ============================================================
# 12. MONTHLY EXTRACTION COVERAGE
# ============================================================

print("\nCalculating monthly extraction coverage...")

monthly_coverage = (
    log_df.groupby([
        "month",
        "status"
    ])
    .agg(
        station_month_tasks=("station_id", "count"),
        measurement_rows=("records", "sum")
    )
    .reset_index()
)

monthly_coverage.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "monthly_extraction_coverage.csv"
    ),
    index=False
)

# ============================================================
# 13. STATION-MONTH COVERAGE
# ============================================================

print("\nCalculating station-month coverage...")

station_month_coverage = (
    log_df.groupby([
        "selected_city",
        "station_id",
        "station_name"
    ])
    .agg(
        months_processed=("month", "nunique"),
        successful_months=(
            "status",
            lambda x: (x == "success").sum()
        ),
        no_data_months=(
            "status",
            lambda x: (x == "no_data").sum()
        ),
        failed_months=(
            "status",
            lambda x: (x == "failed").sum()
        ),
        total_measurement_rows=("records", "sum")
    )
    .reset_index()
)

station_month_coverage["successful_month_percentage"] = (
    station_month_coverage["successful_months"] /
    station_month_coverage["months_processed"] * 100
)

station_month_coverage.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "station_month_coverage.csv"
    ),
    index=False
)

# ============================================================
# 14. STATION-POLLUTANT COVERAGE
# ============================================================

print("\nCalculating station-pollutant coverage...")

station_pollutant_coverage = (
    data.groupby([
        "selected_city",
        "station_id",
        "station_name",
        "parameter_name"
    ])
    .agg(
        total_records=("period_start", "count"),
        unique_days=("period_start", "nunique"),
        months_reporting=("source_month", "nunique"),
        total_observations=("n", "sum"),
        average_daily_mean=("mean", "mean"),
        minimum_value=("min", "min"),
        maximum_value=("max", "max"),
        first_date=("period_start", "min"),
        last_date=("period_start", "max")
    )
    .reset_index()
)

station_pollutant_coverage.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "station_pollutant_coverage.csv"
    ),
    index=False
)

# ============================================================
# 15. MONTHLY POLLUTANT COVERAGE
# ============================================================

print("\nCalculating monthly pollutant coverage...")

data["year_month"] = (
    data["period_start"].dt.to_period("M").astype(str)
)

monthly_pollutant_coverage = (
    data.groupby([
        "selected_city",
        "year_month",
        "parameter_name"
    ])
    .agg(
        stations_reporting=("station_id", "nunique"),
        measurement_records=("period_start", "count"),
        unique_dates=("period_start", "nunique"),
        average_daily_mean=("mean", "mean")
    )
    .reset_index()
)

monthly_pollutant_coverage.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "monthly_pollutant_coverage.csv"
    ),
    index=False
)

# ============================================================
# 16. YEARLY CITY-POLLUTANT COVERAGE
# ============================================================

print("\nCalculating yearly city-pollutant coverage...")

data["year"] = data["period_start"].dt.year

yearly_coverage = (
    data.groupby([
        "selected_city",
        "year",
        "parameter_name"
    ])
    .agg(
        stations_reporting=("station_id", "nunique"),
        measurement_records=("period_start", "count"),
        average_daily_mean=("mean", "mean"),
        minimum_value=("min", "min"),
        maximum_value=("max", "max")
    )
    .reset_index()
)

yearly_coverage.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "yearly_city_pollutant_coverage.csv"
    ),
    index=False
)

# ============================================================
# 17. IDENTIFY MISSING DAILY RECORDS
# ============================================================

print("\nIdentifying missing daily records...")

observed_dates = {}

for key, group in data.groupby(
    ["station_id", "parameter_name", "source_month"]
):

    observed_dates[key] = set(
        group["period_start"]
        .dt.normalize()
        .dropna()
    )

missing_daily_records = []

successful_tasks = log_df[
    log_df["status"] == "success"
]

for _, row in successful_tasks.iterrows():

    station_id = str(row["station_id"])
    month_text = str(row["month"])

    month_period = pd.Period(
        month_text,
        freq="M"
    )

    expected_dates = pd.date_range(
        month_period.start_time,
        month_period.end_time,
        freq="D"
    )

    for pollutant in EXPECTED_POLLUTANTS:

        key = (
            station_id,
            pollutant,
            month_text
        )

        actual_dates = observed_dates.get(
            key,
            set()
        )

        missing_dates = (
            set(expected_dates) - actual_dates
        )

        for missing_date in sorted(missing_dates):

            missing_daily_records.append({

                "selected_city": row["selected_city"],
                "station_id": station_id,
                "station_name": row["station_name"],
                "month": month_text,
                "parameter_name": pollutant,
                "missing_date": missing_date.strftime("%Y-%m-%d")

            })

missing_daily_df = pd.DataFrame(
    missing_daily_records,
    columns=[
        "selected_city",
        "station_id",
        "station_name",
        "month",
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

print(
    "Missing daily records:",
    len(missing_daily_df)
)

# ============================================================
# 18. CITY-WISE DATA COVERAGE
# ============================================================

print("\nCalculating city-wise coverage...")

city_coverage = (
    station_pollutant_coverage.groupby([
        "selected_city",
        "parameter_name"
    ])
    .agg(
        stations_reporting=("station_id", "nunique"),
        total_records=("total_records", "sum"),
        average_days_per_station=("unique_days", "mean"),
        average_months_per_station=("months_reporting", "mean"),
        average_daily_mean=("average_daily_mean", "mean")
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
# 19. STATION SELECTION REVIEW
# ============================================================

print("\nPreparing station selection review...")

station_wide = (
    station_pollutant_coverage.pivot_table(
        index=[
            "selected_city",
            "station_id",
            "station_name"
        ],
        columns="parameter_name",
        values=[
            "total_records",
            "unique_days",
            "months_reporting"
        ],
        aggfunc="first"
    )
)

station_wide.columns = [
    f"{metric}_{pollutant}"
    for metric, pollutant in station_wide.columns
]

station_wide = station_wide.reset_index()

station_wide = station_wide.merge(
    station_month_coverage[
        [
            "station_id",
            "successful_months",
            "no_data_months",
            "failed_months"
        ]
    ],
    on="station_id",
    how="left"
)

for pollutant in EXPECTED_POLLUTANTS:

    for metric in [
        "total_records",
        "unique_days",
        "months_reporting"
    ]:

        column = f"{metric}_{pollutant}"

        if column not in station_wide.columns:
            station_wide[column] = 0

        station_wide[column] = (
            station_wide[column].fillna(0)
        )

station_wide["has_both_pollutants"] = (
    (station_wide["total_records_PM2.5"] > 0) &
    (station_wide["total_records_PM10"] > 0)
)

station_wide["common_months"] = station_wide[
    [
        "months_reporting_PM2.5",
        "months_reporting_PM10"
    ]
].min(axis=1)

station_wide["common_days_minimum"] = station_wide[
    [
        "unique_days_PM2.5",
        "unique_days_PM10"
    ]
].min(axis=1)

station_wide["station_selection_status"] = (
    station_wide["has_both_pollutants"].map({
        True: "Both pollutants available",
        False: "Incomplete pollutant availability"
    })
)

station_wide.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "station_selection_review.csv"
    ),
    index=False
)

# ============================================================
# 20. NO-DATA TASK REVIEW
# ============================================================

no_data_tasks = log_df[
    log_df["status"] == "no_data"
].copy()

no_data_tasks.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "no_data_station_months.csv"
    ),
    index=False
)

# ============================================================
# 21. FINAL VALIDATION REPORT
# ============================================================

print("\nCreating final validation report...")

checks = [

    {
        "validation_check": "Extraction log task count",
        "actual_result": len(log_df),
        "expected_result": 3924,
        "status": "PASS" if len(log_df) == 3924 else "REVIEW"
    },

    {
        "validation_check": "Unique stations in log",
        "actual_result": log_df["station_id"].nunique(),
        "expected_result": 109,
        "status": "PASS" if log_df["station_id"].nunique() == 109 else "REVIEW"
    },

    {
        "validation_check": "Successful station-month tasks",
        "actual_result": len(successful_log),
        "expected_result": 3451,
        "status": "PASS" if len(successful_log) == 3451 else "REVIEW"
    },

    {
        "validation_check": "No-data station-month tasks",
        "actual_result": len(no_data_tasks),
        "expected_result": 473,
        "status": "PASS" if len(no_data_tasks) == 473 else "REVIEW"
    },

    {
        "validation_check": "Loaded measurement records",
        "actual_result": actual_total,
        "expected_result": log_total,
        "status": "PASS" if actual_total == log_total else "REVIEW"
    },

    {
        "validation_check": "Missing required values",
        "actual_result": int(
            data[required_columns].isnull().sum().sum()
        ),
        "expected_result": 0,
        "status": (
            "PASS"
            if data[required_columns].isnull().sum().sum() == 0
            else "REVIEW"
        )
    },

    {
        "validation_check": "Duplicate measurement records",
        "actual_result": len(duplicates),
        "expected_result": 0,
        "status": "PASS" if len(duplicates) == 0 else "REVIEW"
    },

    {
        "validation_check": "Invalid measurements",
        "actual_result": len(invalid_records),
        "expected_result": 0,
        "status": "PASS" if len(invalid_records) == 0 else "REVIEW"
    },

    {
        "validation_check": "File issues",
        "actual_result": len(file_issues_df),
        "expected_result": 0,
        "status": "PASS" if len(file_issues_df) == 0 else "REVIEW"
    }

]

validation_report = pd.DataFrame(checks)

validation_report.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "historical_validation_report.csv"
    ),
    index=False
)

# ============================================================
# 22. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("AIRSCOPE - HISTORICAL COVERAGE ANALYSIS SUMMARY")
print("=" * 70)

print("Extraction period: January 2022 - December 2024")

print(
    "Logged station-month tasks:",
    len(log_df)
)

print(
    "Loaded files:",
    loaded_file_count
)

print(
    "Actual measurement records:",
    actual_total
)

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
    "No-data tasks:",
    len(no_data_tasks)
)

print(
    "File issues:",
    len(file_issues_df)
)

print("\nFinal validation report:")

print(
    validation_report.to_string(index=False)
)

print("\nOutput folder:")
print(OUTPUT_FOLDER)

print("\nScript 17 completed.")
