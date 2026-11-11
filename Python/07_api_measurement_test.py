
import csv
import io
import requests
import getpass
from pathlib import Path
from datetime import datetime

# ============================================================
# AIRSCOPE - API MEASUREMENT TEST
# ============================================================

PROJECT_PATH = Path(r"F:\Manjeet\DA Projects\AirScope")
RAW_PATH = PROJECT_PATH / "Dataset" / "Raw"

STATION_FILE = RAW_PATH / "selected_station_candidates.csv"

OUTPUT_FILE = RAW_PATH / "api_test_measurements.csv"

API_URL = "https://airquality.xkdr.org/v1/measurements"

START_DATE = "2024-01-01"
END_DATE = "2024-01-07"

TARGET_CITY = "Jaipur"
TARGET_POLLUTANTS = ["PM2.5", "PM10"]

# ------------------------------------------------------------
# 1. GET API KEY
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("AIRSCOPE - API MEASUREMENT TEST")
print("=" * 70)

API_KEY = getpass.getpass("\nEnter your XKDR API key: ").strip()

if not API_KEY:
    print("API key cannot be empty.")
    raise SystemExit


# ------------------------------------------------------------
# 2. SELECT A JAIPUR STATION
# ------------------------------------------------------------

try:

    with open(
        STATION_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        station_records = list(reader)

except FileNotFoundError:
    print("\nSelected station file not found.")
    raise SystemExit


jaipur_stations = [
    station for station in station_records
    if station.get("selected_city") == TARGET_CITY
]

if not jaipur_stations:
    print("\nNo Jaipur stations found in selection file.")
    raise SystemExit


# Prefer a station with a full station-level date span
full_coverage_stations = [
    station for station in jaipur_stations
    if station.get(
        "covers_full_period_by_station_dates", ""
    ).lower() == "true"
]

if full_coverage_stations:
    selected_station = full_coverage_stations[0]
else:
    selected_station = jaipur_stations[0]


STATION_ID = selected_station["station_id"]

print("\nSelected City:", TARGET_CITY)
print("Station ID:", STATION_ID)
print("Station Name:", selected_station["station_name"])
print("State:", selected_station["state_name"])


# ------------------------------------------------------------
# 3. PREPARE API REQUEST
# ------------------------------------------------------------

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

params = [
    ("station", STATION_ID),
    ("parameter", "PM2.5"),
    ("parameter", "PM10"),
    ("start", START_DATE),
    ("end", END_DATE),
    ("agg", "daily"),
    ("limit", 500),
    ("format", "csv")
]


# ------------------------------------------------------------
# 4. SEND API REQUEST
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("SENDING API REQUEST")
print("=" * 70)

print("Endpoint:", API_URL)
print("Date Range:", START_DATE, "to", END_DATE)
print("Pollutants:", ", ".join(TARGET_POLLUTANTS))
print("Aggregation: Daily")

try:

    response = requests.get(
        API_URL,
        headers=headers,
        params=params,
        timeout=90
    )

    print("\nStatus Code:", response.status_code)

    response.raise_for_status()

except requests.exceptions.RequestException as error:

    print("\nAPI request failed:")
    print(error)

    if 'response' in locals() and response is not None:
        print("Response:", response.text[:1000])

    raise SystemExit


# ------------------------------------------------------------
# 5. CHECK RESPONSE HEADERS
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("API RESPONSE INFORMATION")
print("=" * 70)

print("Reported Row Count:", response.headers.get("X-Row-Count"))
print("Truncated:", response.headers.get("X-Truncated"))
print("Content Type:", response.headers.get("Content-Type"))


# ------------------------------------------------------------
# 6. READ AND INSPECT CSV RESPONSE
# ------------------------------------------------------------

try:

    import pandas as pd

    df = pd.read_csv(io.StringIO(response.text))

except Exception as error:

    print("\nUnable to parse CSV response:")
    print(error)
    print("\nResponse preview:")
    print(response.text[:2000])
    raise SystemExit


if df.empty:

    print("\nAPI request succeeded, but no measurements were returned.")
    print("We will need to test another station or date range.")
    raise SystemExit


print("\n" + "=" * 70)
print("MEASUREMENT DATA PREVIEW")
print("=" * 70)

print("\nColumns:")
print(df.columns.tolist())

print("\nTotal Records:", len(df))

print("\nPollutant Distribution:")
if "parameter_name" in df.columns:
    print(df["parameter_name"].value_counts())

print("\nFirst 10 Records:")
print(df.head(10).to_string(index=False))


# ------------------------------------------------------------
# 7. VALIDATE POLLUTANT RESULTS
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("POLLUTANT VALIDATION")
print("=" * 70)

if "parameter_name" in df.columns:

    returned_pollutants = set(
        df["parameter_name"].dropna().astype(str)
    )

    for pollutant in TARGET_POLLUTANTS:

        if pollutant in returned_pollutants:
            print(pollutant, ": DATA RECEIVED")
        else:
            print(pollutant, ": NO DATA RETURNED")

else:
    print("parameter_name column not found. Inspect the response schema.")


# ------------------------------------------------------------
# 8. CHECK DATE AND VALUE COLUMNS
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("DATA QUALITY CHECK")
print("=" * 70)

if "period_start" in df.columns:

    df["period_start"] = pd.to_datetime(
        df["period_start"], errors="coerce"
    )

    print("Date column: period_start")
    print("Minimum Date:", df["period_start"].min())
    print("Maximum Date:", df["period_start"].max())

elif "collected_at" in df.columns:

    df["collected_at"] = pd.to_datetime(
        df["collected_at"], errors="coerce"
    )

    print("Date column: collected_at")
    print("Minimum Date:", df["collected_at"].min())
    print("Maximum Date:", df["collected_at"].max())

if "value" in df.columns:

    df["value"] = pd.to_numeric(
        df["value"], errors="coerce"
    )

    print("Missing values:", df["value"].isna().sum())
    print("Minimum measurement:", df["value"].min())
    print("Maximum measurement:", df["value"].max())


# ------------------------------------------------------------
# 9. SAVE TEST DATA
# ------------------------------------------------------------

df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\n" + "=" * 70)
print("API MEASUREMENT TEST COMPLETED")
print("=" * 70)

print("Station:", STATION_ID)
print("Records received:", len(df))
print("Output saved:")
print(OUTPUT_FILE)

print("\nIMPORTANT:")
print(
    "This is a small API test, not the final project dataset. "
    "Do not start bulk extraction until the response is reviewed."
)
