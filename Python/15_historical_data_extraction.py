
import os
import time
import requests
import pandas as pd

from io import StringIO
from datetime import datetime
from getpass import getpass

# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_PATH = r"F:\Manjeet\DA Projects\AirScope"

BASE_URL = "https://airquality.xkdr.org/v1"

CANDIDATE_FILE = os.path.join(
    PROJECT_PATH,
    "Dataset",
    "Raw",
    "selected_station_candidates.csv"
)

OUTPUT_FOLDER = os.path.join(
    PROJECT_PATH,
    "Dataset",
    "Raw",
    "Historical_2022_2024"
)

STATION_FOLDER = os.path.join(
    OUTPUT_FOLDER,
    "Station_Month_Files"
)

LOG_FILE = os.path.join(
    OUTPUT_FOLDER,
    "extraction_log.csv"
)

SUMMARY_FILE = os.path.join(
    OUTPUT_FOLDER,
    "historical_extraction_summary.csv"
)

# ------------------------------------------------------------
# TEST MODE
# ------------------------------------------------------------

# True  = January 2022 only (all selected stations)
# False = January 2022 to December 2024

TEST_MODE = False

if TEST_MODE:
    START_MONTH = "2022-01"
    END_MONTH = "2022-01"
else:
    START_MONTH = "2022-01"
    END_MONTH = "2024-12"

# API request settings
REQUEST_DELAY = 1
MAX_RETRIES = 3
REQUEST_TIMEOUT = 100

# Create folders
os.makedirs(STATION_FOLDER, exist_ok=True)

# ============================================================
# 2. API AUTHENTICATION
# ============================================================

print("=" * 65)
print("AIRSCOPE - HISTORICAL DATA EXTRACTION")
print("=" * 65)

API_KEY = getpass(
    "Enter your XKDR API key: "
)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}

# ============================================================
# 3. LOAD SELECTED STATIONS
# ============================================================

print("\nLoading selected stations...")

if not os.path.exists(CANDIDATE_FILE):
    raise FileNotFoundError(
        f"Station file not found: {CANDIDATE_FILE}"
    )

stations = pd.read_csv(CANDIDATE_FILE)

required_station_columns = [
    "station_id",
    "selected_city",
    "station_name",
    "has_both_pm",
    "overlaps_analysis_period"
]

missing_columns = [
    col for col in required_station_columns
    if col not in stations.columns
]

if missing_columns:
    raise ValueError(
        f"Missing station columns: {missing_columns}"
    )

# Convert selection flags safely
def to_boolean(value):

    return str(value).strip().lower() in [
        "true", "1", "yes"
    ]

stations["has_both_pm"] = (
    stations["has_both_pm"].apply(to_boolean)
)

stations["overlaps_analysis_period"] = (
    stations["overlaps_analysis_period"].apply(to_boolean)
)

# Select stations with both pollutants
# and station-level overlap with the analysis period
stations = stations[
    stations["has_both_pm"] &
    stations["overlaps_analysis_period"]
].copy()

stations["station_id"] = (
    stations["station_id"].astype(str)
)

stations = stations.drop_duplicates(
    subset=["station_id"]
).reset_index(drop=True)

if stations.empty:
    raise ValueError(
        "No eligible stations found. Check the candidate CSV."
    )

print("\nSelected stations:", len(stations))

print("\nCity-wise station count:")

print(
    stations.groupby("selected_city")[
        "station_id"
    ].nunique().to_string()
)

# ============================================================
# 4. GENERATE MONTH LIST
# ============================================================

months = pd.period_range(
    START_MONTH,
    END_MONTH,
    freq="M"
)

total_tasks = len(stations) * len(months)

print("\nExtraction configuration")
print("-" * 45)
print("Test mode:", TEST_MODE)
print("Start month:", START_MONTH)
print("End month:", END_MONTH)
print("Total months:", len(months))
print("Selected stations:", len(stations))
print("Maximum station-month tasks:", total_tasks)

# ============================================================
# 5. LOAD EXISTING EXTRACTION LOG
# ============================================================

log_columns = [
    "station_id",
    "selected_city",
    "station_name",
    "month",
    "status",
    "records",
    "error",
    "extracted_at"
]

if os.path.exists(LOG_FILE):

    log_df = pd.read_csv(
        LOG_FILE,
        dtype={"station_id": str}
    )

    for column in log_columns:

        if column not in log_df.columns:
            log_df[column] = ""

    log_df = log_df[log_columns]

else:

    log_df = pd.DataFrame(
        columns=log_columns
    )

print("\nExisting log entries:", len(log_df))

# ============================================================
# 6. SAVE EXTRACTION LOG
# ============================================================

def save_log(record):

    global log_df

    # Replace previous entry for this station and month
    log_df = log_df[
        ~(
            (log_df["station_id"].astype(str) ==
             str(record["station_id"])) &
            (log_df["month"].astype(str) ==
             str(record["month"]))
        )
    ]

    log_df = pd.concat(
        [
            log_df,
            pd.DataFrame([record])
        ],
        ignore_index=True
    )

    log_df.to_csv(
        LOG_FILE,
        index=False
    )

# ============================================================
# 7. API EXTRACTION FUNCTION
# ============================================================

def extract_station_month(station_id, month):

    start_date = month.start_time.strftime(
        "%Y-%m-%d"
    )

    end_date = month.end_time.strftime(
        "%Y-%m-%d"
    )

    params = [
        ("station", station_id),
        ("parameter", "PM2.5"),
        ("parameter", "PM10"),
        ("start", start_date),
        ("end", end_date),
        ("agg", "daily"),
        ("limit", 500),
        ("format", "csv")
    ]

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            response = requests.get(
                f"{BASE_URL}/measurements",
                headers=HEADERS,
                params=params,
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()

            # Check for truncated API response
            truncated = response.headers.get(
                "X-Truncated", "false"
            ).lower()

            if truncated == "true":

                raise ValueError(
                    "API response was truncated."
                )

            # Handle an empty response
            if not response.text.strip():

                return pd.DataFrame()

            try:

                df = pd.read_csv(
                    StringIO(response.text)
                )

            except pd.errors.EmptyDataError:

                return pd.DataFrame()

            if df.empty:
                return df

            # Validate expected columns
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

            missing = [
                col for col in required_columns
                if col not in df.columns
            ]

            if missing:

                raise ValueError(
                    f"Missing API columns: {missing}"
                )

            # Validate station ID
            df["station_id"] = (
                df["station_id"].astype(str)
            )

            if not (
                df["station_id"] == str(station_id)
            ).all():

                raise ValueError(
                    "Returned station ID does not match request."
                )

            # Validate pollutants
            allowed_pollutants = {
                "PM2.5",
                "PM10"
            }

            returned_pollutants = set(
                df["parameter_name"].dropna()
            )

            if not returned_pollutants.issubset(
                allowed_pollutants
            ):

                raise ValueError(
                    "Unexpected pollutant returned."
                )

            # Validate dates
            df["period_start"] = pd.to_datetime(
                df["period_start"],
                errors="coerce"
            )

            if df["period_start"].isna().any():

                raise ValueError(
                    "Invalid measurement dates returned."
                )

            month_start = pd.Timestamp(start_date)

            next_month = (
                month_start + pd.offsets.MonthBegin(1)
            )

            if not (
                (df["period_start"] >= month_start) &
                (df["period_start"] < next_month)
            ).all():

                raise ValueError(
                    "Measurement date outside requested month."
                )

            # Check duplicate grain
            duplicate_count = df.duplicated(
                subset=[
                    "station_id",
                    "parameter_name",
                    "period_start"
                ]
            ).sum()

            if duplicate_count > 0:

                raise ValueError(
                    "Duplicate station-pollutant-date records."
                )

            return df

        except Exception as error:

            print(
                f"    Attempt {attempt}/{MAX_RETRIES} failed: "
                f"{error}"
            )

            if attempt < MAX_RETRIES:

                time.sleep(3)

    raise RuntimeError(
        "All API extraction attempts failed."
    )

# ============================================================
# 8. MAIN EXTRACTION PROCESS
# ============================================================

print("\nStarting extraction...")
print("=" * 65)

task_number = 0

for _, station in stations.iterrows():

    station_id = str(station["station_id"])
    city = station["selected_city"]
    station_name = station["station_name"]

    for month in months:

        task_number += 1

        month_text = str(month)

        output_file = os.path.join(
            STATION_FOLDER,
            f"{station_id}_{month_text}.csv"
        )

        # ----------------------------------------------------
        # CHECKPOINT / RESUME
        # ----------------------------------------------------

        existing = log_df[
            (log_df["station_id"].astype(str) ==
             station_id) &
            (log_df["month"].astype(str) ==
             month_text)
        ]

        if not existing.empty:

            previous_status = (
                existing.iloc[-1]["status"]
            )

            # Skip previously confirmed no-data tasks
            if previous_status == "no_data":

                print(
                    f"[{task_number}/{total_tasks}] "
                    f"{city} | {station_id} | "
                    f"{month_text} | No data previously"
                )

                continue

            # Skip successful tasks only if the file exists
            if (
                previous_status == "success" and
                os.path.exists(output_file)
            ):

                try:

                    saved_df = pd.read_csv(
                        output_file
                    )

                    if not saved_df.empty:

                        print(
                            f"[{task_number}/{total_tasks}] "
                            f"{city} | {station_id} | "
                            f"{month_text} | Skipped"
                        )

                        continue

                except Exception:
                    pass

        # ----------------------------------------------------
        # EXTRACT DATA
        # ----------------------------------------------------

        print(
            f"\n[{task_number}/{total_tasks}] "
            f"{city} | {station_id} | {month_text}"
        )

        try:

            data = extract_station_month(
                station_id,
                month
            )

            if data.empty:

                status = "no_data"
                records = 0

                if os.path.exists(output_file):
                    os.remove(output_file)

            else:

                data.to_csv(
                    output_file,
                    index=False
                )

                status = "success"
                records = len(data)

            save_log({

                "station_id": station_id,
                "selected_city": city,
                "station_name": station_name,
                "month": month_text,
                "status": status,
                "records": records,
                "error": "",
                "extracted_at": datetime.now().isoformat()

            })

            print(
                f"    Status: {status} | "
                f"Records: {records}"
            )

        except Exception as error:

            save_log({

                "station_id": station_id,
                "selected_city": city,
                "station_name": station_name,
                "month": month_text,
                "status": "failed",
                "records": 0,
                "error": str(error),
                "extracted_at": datetime.now().isoformat()

            })

            print(
                "    Status: failed |",
                error
            )

        time.sleep(REQUEST_DELAY)

# ============================================================
# 9. GENERATE EXTRACTION SUMMARY
# ============================================================

print("\nGenerating extraction summary...")

log_df = pd.read_csv(
    LOG_FILE,
    dtype={"station_id": str}
)

log_df["records"] = pd.to_numeric(
    log_df["records"],
    errors="coerce"
).fillna(0)

# Overall status
print("\nOverall extraction status:")

print(
    log_df["status"].value_counts().to_string()
)

# City-wise summary
city_summary = (
    log_df.groupby([
        "selected_city",
        "status"
    ])
    .agg(
        station_month_tasks=("station_id", "count"),
        measurement_rows=("records", "sum")
    )
    .reset_index()
)

print("\nCity-wise extraction status:")

print(
    city_summary.to_string(index=False)
)

# Monthly summary
monthly_summary = (
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

print("\nMonthly extraction status:")

print(
    monthly_summary.to_string(index=False)
)

# Final city-level summary
summary = (
    log_df.groupby("selected_city")
    .agg(
        station_month_tasks=("station_id", "count"),

        successful_tasks=(
            "status",
            lambda x: (x == "success").sum()
        ),

        no_data_tasks=(
            "status",
            lambda x: (x == "no_data").sum()
        ),

        failed_tasks=(
            "status",
            lambda x: (x == "failed").sum()
        ),

        total_measurement_rows=("records", "sum")

    )
    .reset_index()
)

summary.to_csv(
    SUMMARY_FILE,
    index=False
)

# ============================================================
# 10. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 65)
print("AIRSCOPE HISTORICAL EXTRACTION SUMMARY")
print("=" * 65)

print("Test mode:", TEST_MODE)
print("Selected stations:", len(stations))
print("Months:", len(months))
print("Maximum tasks:", total_tasks)

print(
    "Logged tasks:",
    len(log_df)
)

print(
    "Successful tasks:",
    (log_df["status"] == "success").sum()
)

print(
    "No-data tasks:",
    (log_df["status"] == "no_data").sum()
)

print(
    "Failed tasks:",
    (log_df["status"] == "failed").sum()
)

print(
    "Total measurement rows:",
    int(log_df["records"].sum())
)

print("\nOutput files:")
print("Extraction log:", LOG_FILE)
print("Summary:", SUMMARY_FILE)
print("Station-month files:", STATION_FOLDER)

print("\nScript 15 completed.")
