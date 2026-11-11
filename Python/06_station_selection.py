
import json
import csv
from pathlib import Path
from datetime import datetime

# ============================================================
# AIRSCOPE - FINAL STATION SELECTION
# ============================================================

PROJECT_PATH = Path(r"F:\Manjeet\DA Projects\AirScope")
RAW_PATH = PROJECT_PATH / "Dataset" / "Raw"

STATIONS_FILE = RAW_PATH / "stations.json"

# Proposed analysis period
START_DATE = datetime(2022, 1, 1)
END_DATE = datetime(2024, 12, 31, 23, 59, 59)

# Selected cities and their possible spellings
TARGET_CITIES = {
    "Jaipur": ["jaipur"],
    "Delhi": ["delhi"],
    "Gurugram": ["gurugram", "gurgaon"],
    "Mumbai": ["mumbai"],
    "Bengaluru": ["bengaluru", "bangalore"],
    "Hyderabad": ["hyderabad"]
}

# Required pollutants
REQUIRED_POLLUTANTS = ["PM2.5", "PM10"]


# ------------------------------------------------------------
# 1. LOAD STATION DATA
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("AIRSCOPE - FINAL STATION SELECTION")
print("=" * 70)

try:
    with open(STATIONS_FILE, "r", encoding="utf-8") as file:
        stations = json.load(file)["data"]

    print("\nStation metadata loaded successfully.")

except (FileNotFoundError, json.JSONDecodeError, KeyError) as error:
    print("\nUnable to load station metadata:", error)
    raise SystemExit


# ------------------------------------------------------------
# 2. IDENTIFY CANDIDATE STATIONS
# ------------------------------------------------------------

selected_stations = []
excluded_stations = []

for station in stations:

    city_name = (station.get("city_name") or "").lower()

    selected_city = None

    for city, search_terms in TARGET_CITIES.items():

        if any(term in city_name for term in search_terms):
            selected_city = city
            break

    if selected_city is None:
        continue

    available_pollutants = station.get("parameters") or []

    has_both_pm = all(
        pollutant in available_pollutants
        for pollutant in REQUIRED_POLLUTANTS
    )

    first_seen = station.get("first_seen")
    last_seen = station.get("last_seen")

    if not first_seen or not last_seen:
        overlaps_period = False
        covers_full_period = False

    else:
        first_date = datetime.fromisoformat(first_seen)
        last_date = datetime.fromisoformat(last_seen)

        overlaps_period = (
            first_date <= END_DATE
            and last_date >= START_DATE
        )

        covers_full_period = (
            first_date <= START_DATE
            and last_date >= END_DATE
        )

    record = {
        "selected_city": selected_city,
        "station_id": station.get("station_id"),
        "station_name": station.get("station_name"),
        "city_name": station.get("city_name"),
        "state_name": station.get("state_name"),
        "source": station.get("source"),
        "latitude": station.get("latitude"),
        "longitude": station.get("longitude"),
        "first_seen": first_seen,
        "last_seen": last_seen,
        "total_records": station.get("n_rows"),
        "has_pm25": "PM2.5" in available_pollutants,
        "has_pm10": "PM10" in available_pollutants,
        "has_both_pm": has_both_pm,
        "overlaps_analysis_period": overlaps_period,
        "covers_full_period_by_station_dates": covers_full_period,
        "available_pollutants": ", ".join(available_pollutants)
    }

    if has_both_pm and overlaps_period:
        selected_stations.append(record)
    else:
        excluded_stations.append(record)


# ------------------------------------------------------------
# 3. DISPLAY SELECTION RESULTS
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("STATION SELECTION RESULTS")
print("=" * 70)

print("Proposed period:", START_DATE.date(), "to", END_DATE.date())
print("Selected cities:", len(TARGET_CITIES))
print("Candidate stations:", len(selected_stations))
print("Excluded stations:", len(excluded_stations))

full_span_count = sum(
    station["covers_full_period_by_station_dates"]
    for station in selected_stations
)

print("Candidates with full station-level date span:", full_span_count)


# ------------------------------------------------------------
# 4. CITY-WISE SELECTION SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("CITY-WISE SELECTED STATIONS")
print("=" * 70)

print(f"{'City':<15}{'Candidates':<15}{'Full Date Span':<16}")
print("-" * 46)

for city in TARGET_CITIES:

    city_records = [
        station for station in selected_stations
        if station["selected_city"] == city
    ]

    full_span = sum(
        station["covers_full_period_by_station_dates"]
        for station in city_records
    )

    print(f"{city:<15}{len(city_records):<15}{full_span:<16}")


# ------------------------------------------------------------
# 5. SAVE SELECTED STATIONS
# ------------------------------------------------------------

SELECTED_FILE = RAW_PATH / "selected_station_candidates.csv"

if selected_stations:

    with open(
        SELECTED_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=selected_stations[0].keys()
        )

        writer.writeheader()
        writer.writerows(selected_stations)

    print("\nSelected station candidates saved:")
    print(SELECTED_FILE)

else:
    print("\nNo stations met the selection criteria.")


# ------------------------------------------------------------
# 6. SAVE EXCLUDED STATIONS FOR REVIEW
# ------------------------------------------------------------

EXCLUDED_FILE = RAW_PATH / "excluded_station_review.csv"

if excluded_stations:

    with open(
        EXCLUDED_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=excluded_stations[0].keys()
        )

        writer.writeheader()
        writer.writerows(excluded_stations)

    print("\nExcluded station review saved:")
    print(EXCLUDED_FILE)


# ------------------------------------------------------------
# 7. COMPLETION
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("STATION SELECTION COMPLETED")
print("=" * 70)

print("Required pollutants:", ", ".join(REQUIRED_POLLUTANTS))
print("Analysis period:", START_DATE.date(), "to", END_DATE.date())

print("\nIMPORTANT:")
print(
    "These are candidate stations based on station-level metadata. "
    "Actual pollutant-specific measurement coverage must be verified "
    "after querying the measurements endpoint."
)

print("\nNext: Validate actual measurement availability.")
