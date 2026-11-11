
import json
import csv
from pathlib import Path
from collections import defaultdict

# ============================================================
# AIRSCOPE - POLLUTANT COVERAGE ANALYSIS
# ============================================================

PROJECT_PATH = Path(r"F:\Manjeet\DA Projects\AirScope")
RAW_PATH = PROJECT_PATH / "Dataset" / "Raw"

STATIONS_FILE = RAW_PATH / "stations.json"

# Analysis configuration
START_DATE = "2022-01-01"
END_DATE = "2025-12-31"

TARGET_CITIES = {
    "Jaipur": ["jaipur"],
    "Delhi": ["delhi"],
    "Gurugram": ["gurugram", "gurgaon"],
    "Mumbai": ["mumbai"],
    "Bengaluru": ["bengaluru", "bangalore"],
    "Hyderabad": ["hyderabad"]
}

TARGET_POLLUTANTS = [
    "PM2.5",
    "PM10",
    "NO2",
    "SO2",
    "CO",
    "Ozone"
]

# ------------------------------------------------------------
# 1. LOAD STATION METADATA
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("AIRSCOPE - POLLUTANT COVERAGE ANALYSIS")
print("=" * 75)

try:
    with open(STATIONS_FILE, "r", encoding="utf-8") as file:
        stations = json.load(file)["data"]

    print("\nStation metadata loaded successfully.")

except (FileNotFoundError, json.JSONDecodeError, KeyError) as error:
    print("Unable to load station metadata:", error)
    raise SystemExit


# ------------------------------------------------------------
# 2. FILTER STATIONS FOR SELECTED CITIES
# ------------------------------------------------------------

selected_stations = []

for city, search_terms in TARGET_CITIES.items():

    matches = [
        station for station in stations
        if any(
            term in (station.get("city_name") or "").lower()
            for term in search_terms
        )
    ]

    for station in matches:
        station_copy = station.copy()
        station_copy["selected_city"] = city
        selected_stations.append(station_copy)


# ------------------------------------------------------------
# 3. CITY-WISE POLLUTANT COVERAGE
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("CITY-WISE POLLUTANT COVERAGE")
print("=" * 75)

coverage_summary = []

for city in TARGET_CITIES:

    city_stations = [
        station for station in selected_stations
        if station["selected_city"] == city
    ]

    print(f"\nCITY: {city}")
    print("-" * 65)
    print("Total Stations:", len(city_stations))

    for pollutant in TARGET_POLLUTANTS:

        matching_stations = [
            station for station in city_stations
            if pollutant in station.get("parameters", [])
        ]

        print(
            f"{pollutant:<10} : "
            f"{len(matching_stations)} stations"
        )

        coverage_summary.append({
            "city": city,
            "pollutant": pollutant,
            "total_stations": len(city_stations),
            "stations_with_pollutant": len(matching_stations)
        })


# ------------------------------------------------------------
# 4. IDENTIFY STATIONS WITH BOTH PM2.5 AND PM10
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("STATIONS WITH BOTH PM2.5 AND PM10")
print("=" * 75)

dual_pm_stations = []

for station in selected_stations:

    available = station.get("parameters") or []

    if "PM2.5" in available and "PM10" in available:
        dual_pm_stations.append(station)

        print("\nCity:", station["selected_city"])
        print("Station:", station.get("station_name"))
        print("Station ID:", station.get("station_id"))
        print("First Seen:", station.get("first_seen"))
        print("Last Seen:", station.get("last_seen"))


# ------------------------------------------------------------
# 5. CHECK STATION-LEVEL DATE COVERAGE
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("STATION-LEVEL HISTORICAL COVERAGE")
print("=" * 75)

station_review = []

for station in selected_stations:

    first_seen = station.get("first_seen") or ""
    last_seen = station.get("last_seen") or ""

    overlaps_period = (
        bool(first_seen and last_seen)
        and first_seen[:10] <= END_DATE
        and last_seen[:10] >= START_DATE
    )

    sufficient_for_period = (
        bool(first_seen and last_seen)
        and first_seen[:10] <= START_DATE
        and last_seen[:10] >= END_DATE
    )

    record = {
        "selected_city": station["selected_city"],
        "station_id": station.get("station_id"),
        "station_name": station.get("station_name"),
        "actual_city": station.get("city_name"),
        "state": station.get("state_name"),
        "source": station.get("source"),
        "latitude": station.get("latitude"),
        "longitude": station.get("longitude"),
        "first_seen": first_seen,
        "last_seen": last_seen,
        "total_records": station.get("n_rows"),
        "has_pm25": "PM2.5" in (station.get("parameters") or []),
        "has_pm10": "PM10" in (station.get("parameters") or []),
        "has_no2": "NO2" in (station.get("parameters") or []),
        "has_so2": "SO2" in (station.get("parameters") or []),
        "has_co": "CO" in (station.get("parameters") or []),
        "has_ozone": "Ozone" in (station.get("parameters") or []),
        "has_both_pm": (
            "PM2.5" in (station.get("parameters") or [])
            and "PM10" in (station.get("parameters") or [])
        ),
        "overlaps_analysis_period": overlaps_period,
        "covers_full_analysis_period_by_station_dates":
            sufficient_for_period
    }

    station_review.append(record)


# ------------------------------------------------------------
# 6. CITY-WISE STATION SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("CITY-WISE STATION SUMMARY")
print("=" * 75)

print(
    f"{'City':<15}"
    f"{'Total':<10}"
    f"{'Both PM':<12}"
    f"{'Period Overlap':<17}"
    f"{'Full Date Span':<15}"
)

print("-" * 69)

for city in TARGET_CITIES:

    records = [
        record for record in station_review
        if record["selected_city"] == city
    ]

    total = len(records)

    both_pm = sum(
        record["has_both_pm"] for record in records
    )

    overlapping = sum(
        record["overlaps_analysis_period"] for record in records
    )

    full_span = sum(
        record["covers_full_analysis_period_by_station_dates"]
        for record in records
    )

    print(
        f"{city:<15}"
        f"{total:<10}"
        f"{both_pm:<12}"
        f"{overlapping:<17}"
        f"{full_span:<15}"
    )


# ------------------------------------------------------------
# 7. SAVE ANALYSIS OUTPUTS
# ------------------------------------------------------------

coverage_file = RAW_PATH / "pollutant_coverage_summary.csv"

with open(
    coverage_file, "w", newline="", encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=coverage_summary[0].keys()
    )

    writer.writeheader()
    writer.writerows(coverage_summary)


station_file = RAW_PATH / "station_coverage_review.csv"

with open(
    station_file, "w", newline="", encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=station_review[0].keys()
    )

    writer.writeheader()
    writer.writerows(station_review)


# ------------------------------------------------------------
# 8. FINAL SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("POLLUTANT COVERAGE ANALYSIS COMPLETED")
print("=" * 75)

print("Cities investigated:", len(TARGET_CITIES))
print("Selected stations:", len(selected_stations))
print("Stations with both PM2.5 and PM10:", len(dual_pm_stations))

print("\nFiles saved:")
print(coverage_file)
print(station_file)

print("\nAnalysis period:", START_DATE, "to", END_DATE)

print("\nNote:")
print(
    "Date coverage is based on station-level first_seen and last_seen. "
    "It does not confirm continuous or pollutant-specific data availability."
)
