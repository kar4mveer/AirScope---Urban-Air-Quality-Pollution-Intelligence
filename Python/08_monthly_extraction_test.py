
import requests
import pandas as pd
import getpass
from pathlib import Path

# ============================================================
# AIRSCOPE - FULL MONTH MEASUREMENT EXTRACTION TEST
# ============================================================

PROJECT_PATH = Path(r"F:\Manjeet\DA Projects\AirScope")
RAW_PATH = PROJECT_PATH / "Dataset" / "Raw"

API_URL = "https://airquality.xkdr.org/v1/measurements"

# Test configuration
STATION_ID = "site_1393"
STATION_NAME = "Adarsh Nagar, Jaipur - RSPCB"

START_DATE = "2024-01-01"
END_DATE = "2024-01-31"

POLLUTANTS = ["PM2.5", "PM10"]

OUTPUT_FILE = RAW_PATH / "january_2024_measurements.csv"
SUMMARY_FILE = RAW_PATH / "january_2024_quality_report.csv"


# ------------------------------------------------------------
# 1. API AUTHENTICATION
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("AIRSCOPE - FULL MONTH EXTRACTION TEST")
print("=" * 75)

API_KEY = getpass.getpass("\nEnter your XKDR API key: ").strip()

if not API_KEY:
    print("API key cannot be empty.")
    raise SystemExit


# ------------------------------------------------------------
# 2. DISPLAY EXTRACTION CONFIGURATION
# ------------------------------------------------------------

print("\nEXTRACTION CONFIGURATION")
print("-" * 75)

print("City: Jaipur")
print("Station:", STATION_NAME)
print("Station ID:", STATION_ID)
print("Start Date:", START_DATE)
print("End Date:", END_DATE)
print("Pollutants:", ", ".join(POLLUTANTS))
print("Aggregation: Daily")


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
# 4. FETCH MEASUREMENTS
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("FETCHING JANUARY 2024 MEASUREMENTS")
print("=" * 75)

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

    if "response" in locals():
        print("Response:", response.text[:1500])

    raise SystemExit


# ------------------------------------------------------------
# 5. READ API RESPONSE
# ------------------------------------------------------------

print("\nAPI RESPONSE INFORMATION")
print("-" * 75)

print("Reported Row Count:", response.headers.get("X-Row-Count"))
print("Truncated:", response.headers.get("X-Truncated"))
print("Content Type:", response.headers.get("Content-Type"))

try:

    from io import StringIO

    df = pd.read_csv(StringIO(response.text))

except Exception as error:

    print("\nUnable to read API response:", error)
    print(response.text[:2000])
    raise SystemExit


if df.empty:

    print("\nNo measurement records returned.")
    raise SystemExit


# ------------------------------------------------------------
# 6. VALIDATE RESPONSE STRUCTURE
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("DATASET STRUCTURE")
print("=" * 75)

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
    column for column in required_columns
    if column not in df.columns
]

if missing_columns:

    print("Missing expected columns:", missing_columns)
    print("Actual columns:", df.columns.tolist())
    raise SystemExit

print("Columns validated successfully.")
print("Total records received:", len(df))


# ------------------------------------------------------------
# 7. DATA TYPE CONVERSION
# ------------------------------------------------------------

df["period_start"] = pd.to_datetime(
    df["period_start"],
    errors="coerce"
)

for column in ["mean", "min", "max", "n"]:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# ------------------------------------------------------------
# 8. POLLUTANT-WISE RECORD SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("POLLUTANT-WISE MEASUREMENT SUMMARY")
print("=" * 75)

summary_records = []

for pollutant in POLLUTANTS:

    pollutant_df = df[
        df["parameter_name"] == pollutant
    ].copy()

    valid_dates = pollutant_df[
        pollutant_df["period_start"].notna()
    ]["period_start"].dt.date

    unique_dates = set(valid_dates)

    expected_dates = set(
        pd.date_range(
            START_DATE,
            END_DATE,
            freq="D"
        ).date
    )

    missing_dates = sorted(
        expected_dates - unique_dates
    )

    print("\nPollutant:", pollutant)
    print("Records:", len(pollutant_df))
    print("Unique measurement dates:", len(unique_dates))
    print("Missing dates:", len(missing_dates))

    if missing_dates:
        print("Missing date list:", missing_dates)

    if not pollutant_df.empty:

        print(
            "Average of daily means:",
            round(pollutant_df["mean"].mean(), 2)
        )

        print(
            "Minimum daily minimum:",
            pollutant_df["min"].min()
        )

        print(
            "Maximum daily maximum:",
            pollutant_df["max"].max()
        )

        print(
            "Total underlying observations:",
            pollutant_df["n"].sum()
        )

    summary_records.append({
        "station_id": STATION_ID,
        "station_name": STATION_NAME,
        "pollutant": pollutant,
        "expected_days": len(expected_dates),
        "records_returned": len(pollutant_df),
        "unique_dates": len(unique_dates),
        "missing_dates": len(missing_dates),
        "total_observations": pollutant_df["n"].sum(),
        "average_of_daily_means": pollutant_df["mean"].mean(),
        "minimum_daily_min": pollutant_df["min"].min(),
        "maximum_daily_max": pollutant_df["max"].max()
    })


# ------------------------------------------------------------
# 9. CHECK DATA QUALITY
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("DATA QUALITY CHECK")
print("=" * 75)

print("Missing station IDs:", df["station_id"].isna().sum())
print("Missing pollutant names:", df["parameter_name"].isna().sum())
print("Missing dates:", df["period_start"].isna().sum())
print("Missing daily means:", df["mean"].isna().sum())
print("Missing minimum values:", df["min"].isna().sum())
print("Missing maximum values:", df["max"].isna().sum())
print("Missing observation counts:", df["n"].isna().sum())

print(
    "Duplicate station-pollutant-date rows:",
    df.duplicated(
        subset=["station_id", "parameter_name", "period_start"]
    ).sum()
)

print(
    "Rows with non-positive observation counts:",
    (df["n"].fillna(0) <= 0).sum()
)


# ------------------------------------------------------------
# 10. SAVE RAW MEASUREMENTS
# ------------------------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print("\nMeasurements saved:")
print(OUTPUT_FILE)


# ------------------------------------------------------------
# 11. SAVE QUALITY REPORT
# ------------------------------------------------------------

quality_df = pd.DataFrame(summary_records)

quality_df.to_csv(
    SUMMARY_FILE,
    index=False,
    encoding="utf-8-sig"
)

print("\nQuality report saved:")
print(SUMMARY_FILE)


# ------------------------------------------------------------
# 12. FINAL RESULTS
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("FULL MONTH EXTRACTION TEST COMPLETED")
print("=" * 75)

print("Station:", STATION_ID)
print("Period:", START_DATE, "to", END_DATE)
print("Total records:", len(df))
print("Pollutants received:", df["parameter_name"].nunique())

print("\nGenerated files:")
print("1.", OUTPUT_FILE)
print("2.", SUMMARY_FILE)

print("\nIMPORTANT:")
print(
    "Daily record counts do not guarantee complete hourly coverage. "
    "Review the observation counts and missing dates before bulk extraction."
)
