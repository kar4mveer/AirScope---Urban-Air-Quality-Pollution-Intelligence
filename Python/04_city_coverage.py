
import json
from pathlib import Path

# ============================================================
# AIRSCOPE - CITY COVERAGE AND POLLUTANT AVAILABILITY ANALYSIS
# ============================================================

PROJECT_PATH = Path(r"F:\Manjeet\DA Projects\AirScope")
RAW_PATH = PROJECT_PATH / "Dataset" / "Raw"

STATIONS_FILE = RAW_PATH / "stations.json"
PARAMETERS_FILE = RAW_PATH / "parameters.json"


# ------------------------------------------------------------
# 1. LOAD SAVED METADATA
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("AIRSCOPE - CITY COVERAGE ANALYSIS")
print("=" * 70)

try:
    with open(STATIONS_FILE, "r", encoding="utf-8") as file:
        stations = json.load(file)["data"]

    with open(PARAMETERS_FILE, "r", encoding="utf-8") as file:
        parameters = json.load(file)["data"]

    print("\nMetadata files loaded successfully.")

except FileNotFoundError as error:
    print("\nError: Required metadata file not found.")
    print(error)
    raise SystemExit

except (json.JSONDecodeError, KeyError) as error:
    print("\nError: Unable to read metadata structure.")
    print(error)
    raise SystemExit


# ------------------------------------------------------------
# 2. DEFINE TARGET CITIES
# ------------------------------------------------------------

target_cities = {
    "Jaipur": ["jaipur"],
    "Delhi": ["delhi"],
    "Gurugram": ["gurugram", "gurgaon"],
    "Mumbai": ["mumbai"],
    "Bengaluru": ["bengaluru", "bangalore"],
    "Hyderabad": ["hyderabad"]
}


# ------------------------------------------------------------
# 3. CITY-WISE STATION COVERAGE
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("CITY-WISE MONITORING STATION COVERAGE")
print("=" * 70)

for display_name, search_terms in target_cities.items():

    matches = [
        station for station in stations
        if any(
            term in (station.get("city_name") or "").lower()
            for term in search_terms
        )
    ]

    print(f"\n\nCITY: {display_name}")
    print("-" * 70)

    print("Total Monitoring Stations:", len(matches))

    if not matches:
        print("No matching stations found.")
        continue

    for index, station in enumerate(matches, start=1):

        print(f"\nStation {index}")
        print("Station ID:", station.get("station_id"))
        print("Station Name:", station.get("station_name"))
        print("City:", station.get("city_name"))
        print("State:", station.get("state_name"))
        print("Data Source:", station.get("source"))
        print("First Available Record:", station.get("first_seen"))
        print("Last Available Record:", station.get("last_seen"))
        print("Total Measurements:", f'{station.get("n_rows", 0):,}')

        print(
            "Available Pollutants:",
            ", ".join(station.get("parameters", []))
        )


# ------------------------------------------------------------
# 4. COMPLETE POLLUTANT CATALOGUE
# ------------------------------------------------------------

print("\n\n" + "=" * 70)
print("COMPLETE POLLUTANT CATALOGUE")
print("=" * 70)

for parameter in parameters:

    print("\nPollutant:", parameter.get("parameter_name"))
    print("Unit:", parameter.get("unit"))
    print("Available Stations:", parameter.get("n_stations"))
    print("Total Measurements:", f'{parameter.get("n_rows", 0):,}')
    print("First Available Record:", parameter.get("first_seen"))
    print("Last Available Record:", parameter.get("last_seen"))


# ------------------------------------------------------------
# 5. CITY COVERAGE SUMMARY
# ------------------------------------------------------------

print("\n\n" + "=" * 70)
print("CITY COVERAGE SUMMARY")
print("=" * 70)

print(
    f"\n{'City':<15}"
    f"{'State':<22}"
    f"{'Stations':<12}"
    f"{'Total Records':<18}"
)

print("-" * 67)

for display_name, search_terms in target_cities.items():

    matches = [
        station for station in stations
        if any(
            term in (station.get("city_name") or "").lower()
            for term in search_terms
        )
    ]

    if matches:
        state = matches[0].get("state_name", "Unknown")
        total_records = sum(
            station.get("n_rows", 0) for station in matches
        )
    else:
        state = "Not available"
        total_records = 0

    print(
        f"{display_name:<15}"
        f"{state:<22}"
        f"{len(matches):<12}"
        f"{total_records:,}"
    )


# ------------------------------------------------------------
# 6. SAVE CITY COVERAGE SUMMARY
# ------------------------------------------------------------

summary = []

for display_name, search_terms in target_cities.items():

    matches = [
        station for station in stations
        if any(
            term in (station.get("city_name") or "").lower()
            for term in search_terms
        )
    ]

    for station in matches:

        summary.append({
            "selected_city": display_name,
            "station_id": station.get("station_id"),
            "station_name": station.get("station_name"),
            "city_name": station.get("city_name"),
            "state_name": station.get("state_name"),
            "source": station.get("source"),
            "latitude": station.get("latitude"),
            "longitude": station.get("longitude"),
            "first_seen": station.get("first_seen"),
            "last_seen": station.get("last_seen"),
            "n_rows": station.get("n_rows"),
            "parameters": ", ".join(
                station.get("parameters", [])
            )
        })

OUTPUT_FILE = RAW_PATH / "city_coverage_summary.json"

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(summary, file, indent=4, ensure_ascii=False)


# ------------------------------------------------------------
# 7. COMPLETION
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("CITY COVERAGE ANALYSIS COMPLETED")
print("=" * 70)

print("\nTotal cities investigated:", len(target_cities))
print("Total matching stations:", len(summary))
print("Summary saved to:", OUTPUT_FILE)

print("\nNext Step: Finalise cities and select the analysis period.")
