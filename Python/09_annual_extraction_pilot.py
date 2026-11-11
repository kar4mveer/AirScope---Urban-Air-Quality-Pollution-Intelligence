
import requests
import pandas as pd
import getpass
import time
import calendar
from pathlib import Path
from io import StringIO

# ============================================================
# AIRSCOPE - FULL YEAR EXTRACTION PILOT
# ============================================================

PROJECT_PATH = Path(r"F:\Manjeet\DA Projects\AirScope")
RAW_PATH = PROJECT_PATH / "Dataset" / "Raw"

API_URL = "https://airquality.xkdr.org/v1/measurements"

STATION_ID = "site_1393"
STATION_NAME = "Adarsh Nagar, Jaipur - RSPCB"

YEAR = 2024
POLLUTANTS = ["PM2.5", "PM10"]

OUTPUT_FILE = RAW_PATH / "jaipur_2024_annual_pilot.csv"
REPORT_FILE = RAW_PATH / "jaipur_2024_annual_quality_report.csv"


# ------------------------------------------------------------
# 1. API AUTHENTICATION
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("AIRSCOPE - ANNUAL EXTRACTION PILOT")
print("=" * 75)

API_KEY = getpass.getpass("\nEnter your XKDR API key: ").strip()

if not API_KEY:
    print("API key cannot be empty.")
    raise SystemExit

headers = {
    "Authorization": f"Bearer {API_KEY}"
}


# ------------------------------------------------------------
# 2. EXTRACT DATA MONTH BY MONTH
# ------------------------------------------------------------

monthly_data = []

for month in range(1, 13):

    start_date = f"{YEAR}-{month:02d}-01"

    last_day = calendar.monthrange(YEAR, month)[1]
    end_date = f"{YEAR}-{month:02d}-{last_day}"

    print("\n" + "-" * 65)
    print(f"Fetching: {calendar.month_name[month]} {YEAR}")
    print("Period:", start_date, "to", end_date)

    params = [
        ("station", STATION_ID),
        ("parameter", "PM2.5"),
        ("parameter", "PM10"),
        ("start", start_date),
        ("end", end_date),
        ("agg", "daily"),
        ("limit", 500),
        ("format", "csv")
    ]

    success = False

    for attempt in range(1, 4):

        try:

            response = requests.get(
                API_URL,
                headers=headers,
                params=params,
                timeout=90
            )

            response.raise_for_status()

            truncated = response.headers.get(
                "X-Truncated", "false"
            ).lower()

            if truncated == "true":
                print("WARNING: API response is truncated.")
                raise RuntimeError("Truncated monthly response")

            month_df = pd.read_csv(
                StringIO(response.text)
            )

            if not month_df.empty:

                month_df["extraction_month"] = month

                monthly_data.append(month_df)

            print("Status:", response.status_code)
            print("Records received:", len(month_df))
            print("Truncated:", truncated)

            success = True
            break

        except Exception as error:

            print(f"Attempt {attempt} failed:", error)

            if attempt < 3:
                time.sleep(3)

    if not success:

        print("\nExtraction stopped.")
        print("Failed month:", calendar.month_name[month])
        print("Please resolve the error before continuing.")
        raise SystemExit

    time.sleep(1)


# ------------------------------------------------------------
# 3. COMBINE MONTHLY DATA
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("COMBINING ANNUAL DATA")
print("=" * 75)

if not monthly_data:
    print("No measurements were received.")
    raise SystemExit

df = pd.concat(
    monthly_data,
    ignore_index=True
)

df["period_start"] = pd.to_datetime(
    df["period_start"],
    errors="coerce"
)

for column in ["mean", "min", "max", "n"]:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )

print("Total annual records:", len(df))


# ------------------------------------------------------------
# 4. ANNUAL POLLUTANT SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("ANNUAL POLLUTANT SUMMARY")
print("=" * 75)

quality_report = []

for pollutant in POLLUTANTS:

    subset = df[
        df["parameter_name"] == pollutant
    ].copy()

    dates = set(
        subset["period_start"].dropna().dt.date
    )

    expected_dates = set(
        pd.date_range(
            f"{YEAR}-01-01",
            f"{YEAR}-12-31",
            freq="D"
        ).date
    )

    missing_dates = sorted(
        expected_dates - dates
    )

    print("\nPollutant:", pollutant)
    print("Records:", len(subset))
    print("Unique dates:", len(dates))
    print("Missing dates:", len(missing_dates))
    print("Underlying observations:", subset["n"].sum())
    print(
        "Average of daily means:",
        round(subset["mean"].mean(), 2)
        if not subset.empty else None
    )

    quality_report.append({
        "year": YEAR,
        "station_id": STATION_ID,
        "pollutant": pollutant,
        "expected_days": len(expected_dates),
        "records_received": len(subset),
        "unique_dates": len(dates),
        "missing_dates": len(missing_dates),
        "total_observations": subset["n"].sum(),
        "average_daily_mean": subset["mean"].mean()
    })


# ------------------------------------------------------------
# 5. DATA QUALITY VALIDATION
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("ANNUAL DATA QUALITY CHECK")
print("=" * 75)

print("Missing station IDs:", df["station_id"].isna().sum())
print("Missing pollutant names:", df["parameter_name"].isna().sum())
print("Missing dates:", df["period_start"].isna().sum())
print("Missing means:", df["mean"].isna().sum())

duplicates = df.duplicated(
    subset=["station_id", "parameter_name", "period_start"]
).sum()

print("Duplicate station-pollutant-date rows:", duplicates)

print("\nPollutant record distribution:")
print(df["parameter_name"].value_counts())


# ------------------------------------------------------------
# 6. SAVE ANNUAL DATA
# ------------------------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

pd.DataFrame(quality_report).to_csv(
    REPORT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print("\n" + "=" * 75)
print("ANNUAL EXTRACTION PILOT COMPLETED")
print("=" * 75)

print("Station:", STATION_NAME)
print("Year:", YEAR)
print("Total records:", len(df))

print("\nFiles saved:")
print(OUTPUT_FILE)
print(REPORT_FILE)

print("\nIMPORTANT:")
print(
    "Review missing dates, duplicate records and observation counts "
    "before scaling this process to additional stations."
)
