
import os
import time
import getpass
import requests
import pandas as pd
from datetime import datetime

# =====================================================
# 1. PROJECT CONFIGURATION
# =====================================================

BASE_URL = "https://airquality.xkdr.org/v1"

PROJECT_PATH = r"F:\Manjeet\DA Projects\AirScope"

CANDIDATE_FILE = os.path.join(
    PROJECT_PATH,
    "Dataset", "Raw", "selected_station_candidates.csv"
)

OUTPUT_FOLDER = os.path.join(
    PROJECT_PATH,
    "Dataset", "Raw", "Jan_2024_Pilot_By_Station"
)

COMBINED_FILE = os.path.join(
    PROJECT_PATH,
    "Dataset", "Raw", "all_cities_january_2024_pilot.csv"
)

LOG_FILE = os.path.join(
    PROJECT_PATH,
    "Dataset", "Raw", "station_extraction_log.csv"
)

START_DATE = "2024-01-01"
END_DATE = "2024-01-31"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# =====================================================
# 2. API AUTHENTICATION
# =====================================================

API_KEY = getpass.getpass("Enter your XKDR API key: ")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}

# =====================================================
# 3. LOAD SELECTED STATIONS
# =====================================================

print("\nLoading selected station candidates...")

stations = pd.read_csv(CANDIDATE_FILE)

# Handle boolean values whether stored as True or text
stations["has_both_pm"] = (
    stations["has_both_pm"].astype(str).str.lower() == "true"
)

stations["overlaps_analysis_period"] = (
    stations["overlaps_analysis_period"]
    .astype(str).str.lower() == "true"
)

stations = stations[
    (stations["has_both_pm"]) &
    (stations["overlaps_analysis_period"])
].copy()

stations = stations.drop_duplicates(subset=["station_id"])

print("Selected stations:", len(stations))
print("\nStations by city:")
print(stations.groupby("selected_city")["station_id"].count())

# =====================================================
# 4. LOAD EXISTING EXTRACTION LOG
# =====================================================

if os.path.exists(LOG_FILE):
    log_df = pd.read_csv(LOG_FILE)
else:
    log_df = pd.DataFrame(columns=[
        "station_id",
        "selected_city",
        "station_name",
        "status",
        "records",
        "error",
        "extracted_at"
    ])

# =====================================================
# 5. EXTRACTION FUNCTION
# =====================================================

def extract_station(station_id):

    params = [
        ("station", station_id),
        ("parameter", "PM2.5"),
        ("parameter", "PM10"),
        ("start", START_DATE),
        ("end", END_DATE),
        ("agg", "daily"),
        ("limit", 500),
        ("format", "csv")
    ]

    for attempt in range(1, 4):

        try:
            response = requests.get(
                f"{BASE_URL}/measurements",
                headers=HEADERS,
                params=params,
                timeout=100
            )

            response.raise_for_status()

            if response.headers.get(
                "X-Truncated", "false"
            ).lower() == "true":

                raise ValueError(
                    "API response was truncated."
                )

            from io import StringIO

            df = pd.read_csv(StringIO(response.text))

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
                raise ValueError(
                    f"Missing columns: {missing_columns}"
                )

            if not df.empty:
                df["period_start"] = pd.to_datetime(
                    df["period_start"],
                    errors="coerce"
                )

                df["mean"] = pd.to_numeric(
                    df["mean"], errors="coerce"
                )

                df["min"] = pd.to_numeric(
                    df["min"], errors="coerce"
                )

                df["max"] = pd.to_numeric(
                    df["max"], errors="coerce"
                )

                df["n"] = pd.to_numeric(
                    df["n"], errors="coerce"
                )

                valid_parameters = {"PM2.5", "PM10"}

                if not set(df["parameter_name"].dropna()).issubset(
                    valid_parameters
                ):
                    raise ValueError(
                        "Unexpected pollutant in API response."
                    )

                if not (df["station_id"].astype(str) == str(
                    station_id
                )).all():
                    raise ValueError(
                        "Station ID mismatch in API response."
                    )

            return df

        except Exception as error:

            print(
                f"  Attempt {attempt}/3 failed: {error}"
            )

            if attempt < 3:
                time.sleep(3)

    raise RuntimeError("All 3 extraction attempts failed.")

# =====================================================
# 6. SAVE LOG FUNCTION
# =====================================================

def update_log(record):

    global log_df

    log_df = log_df[
        log_df["station_id"].astype(str) !=
        str(record["station_id"])
    ]

    log_df = pd.concat(
        [log_df, pd.DataFrame([record])],
        ignore_index=True
    )

    log_df.to_csv(LOG_FILE, index=False)

# =====================================================
# 7. EXTRACT DATA FOR ALL STATIONS
# =====================================================

print("\nStarting January 2024 extraction...")
print("=" * 60)

total = len(stations)

for index, row in stations.iterrows():

    station_id = str(row["station_id"])
    city = row["selected_city"]
    station_name = row["station_name"]

    station_file = os.path.join(
        OUTPUT_FOLDER,
        f"{station_id}.csv"
    )

    # Skip only stations previously extracted successfully
    existing = log_df[
        (log_df["station_id"].astype(str) == station_id) &
        (log_df["status"] == "success")
    ]

    if (
        not existing.empty and
        os.path.exists(station_file)
    ):
        try:
            saved_df = pd.read_csv(station_file)

            if not saved_df.empty:
                print(
                    f"[{index + 1}/{total}] "
                    f"{city} | {station_id} - Already completed"
                )
                continue

        except Exception:
            pass

    print(
        f"\n[{index + 1}/{total}] "
        f"Extracting {city} | {station_id} | {station_name}"
    )

    try:

        df = extract_station(station_id)

        if df.empty:

            status = "no_data"
            records = 0
            error_message = "API returned no records."

            if os.path.exists(station_file):
                os.remove(station_file)

        else:

            df.to_csv(station_file, index=False)

            status = "success"
            records = len(df)
            error_message = ""

        update_log({
            "station_id": station_id,
            "selected_city": city,
            "station_name": station_name,
            "status": status,
            "records": records,
            "error": error_message,
            "extracted_at": datetime.now().isoformat()
        })

        print(
            f"  Status: {status} | Records: {records}"
        )

    except Exception as error:

        update_log({
            "station_id": station_id,
            "selected_city": city,
            "station_name": station_name,
            "status": "failed",
            "records": 0,
            "error": str(error),
            "extracted_at": datetime.now().isoformat()
        })

        print("  Extraction failed:", error)

    # Small delay between station requests
    time.sleep(1)

# =====================================================
# 8. COMBINE SUCCESSFUL STATION FILES
# =====================================================

print("\nCombining extracted station data...")

all_data = []

for _, row in stations.iterrows():

    station_id = str(row["station_id"])

    station_file = os.path.join(
        OUTPUT_FOLDER,
        f"{station_id}.csv"
    )

    if not os.path.exists(station_file):
        continue

    try:
        df = pd.read_csv(station_file)

        if df.empty:
            continue

        # Add station metadata
        df["selected_city"] = row["selected_city"]
        df["station_name"] = row["station_name"]
        df["city_name"] = row["city_name"]
        df["state_name"] = row["state_name"]
        df["source"] = row["source"]
        df["latitude"] = row["latitude"]
        df["longitude"] = row["longitude"]

        all_data.append(df)

    except Exception as error:
        print(
            f"Could not combine {station_id}: {error}"
        )

if all_data:

    combined_df = pd.concat(
        all_data,
        ignore_index=True
    )

    combined_df["period_start"] = pd.to_datetime(
        combined_df["period_start"],
        errors="coerce"
    )

    combined_df = combined_df.sort_values(
        ["selected_city", "station_id",
         "parameter_name", "period_start"]
    )

    combined_df.to_csv(
        COMBINED_FILE,
        index=False
    )

    print("\nCombined dataset saved successfully.")

else:

    combined_df = pd.DataFrame()
    print("\nNo successful station data available.")

# =====================================================
# 9. EXTRACTION SUMMARY
# =====================================================

print("\n" + "=" * 60)
print("JANUARY 2024 EXTRACTION SUMMARY")
print("=" * 60)

print("Total selected stations:", total)

print("\nStatus summary:")
print(log_df["status"].value_counts())

print("\nCity-wise extraction summary:")

print(
    log_df.groupby(
        ["selected_city", "status"]
    )["station_id"].count()
)

print("\nTotal measurement rows:", len(combined_df))

if not combined_df.empty:

    print(
        "Unique stations:",
        combined_df["station_id"].nunique()
    )

    print(
        "Pollutants:",
        combined_df["parameter_name"].unique()
    )

    print(
        "Date range:",
        combined_df["period_start"].min(),
        "to",
        combined_df["period_start"].max()
    )

print("\nOutput files:")
print("Combined dataset:", COMBINED_FILE)
print("Extraction log:", LOG_FILE)
print("Individual station files:", OUTPUT_FOLDER)

print("\nScript 10 completed.")
