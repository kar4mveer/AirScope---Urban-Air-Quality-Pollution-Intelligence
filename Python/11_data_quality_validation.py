
import os
import pandas as pd

# =====================================================
# 1. FILE PATHS
# =====================================================

PROJECT_PATH = r"F:\Manjeet\DA Projects\AirScope"

INPUT_FILE = os.path.join(
    PROJECT_PATH,
    "Dataset", "Raw",
    "all_cities_january_2024_pilot.csv"
)

OUTPUT_FOLDER = os.path.join(
    PROJECT_PATH,
    "Dataset", "Raw"
)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# =====================================================
# 2. LOAD DATA
# =====================================================

print("Loading AirScope dataset...")

df = pd.read_csv(INPUT_FILE)

df["period_start"] = pd.to_datetime(
    df["period_start"],
    errors="coerce"
)

print("Total rows:", len(df))
print("Unique stations:", df["station_id"].nunique())

# =====================================================
# 3. MISSING VALUE CHECK
# =====================================================

print("\nChecking missing values...")

important_columns = [
    "station_id",
    "parameter_name",
    "period_start",
    "mean",
    "min",
    "max",
    "n",
    "selected_city"
]

missing_report = pd.DataFrame({
    "column": important_columns,
    "missing_count": [
        df[col].isna().sum()
        for col in important_columns
    ]
})

missing_report.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "missing_values_report.csv"
    ),
    index=False
)

print(missing_report.to_string(index=False))

# =====================================================
# 4. DUPLICATE CHECK
# =====================================================

print("\nChecking duplicate records...")

duplicate_count = df.duplicated(
    subset=[
        "station_id",
        "parameter_name",
        "period_start"
    ]
).sum()

print("Duplicate station-pollutant-date rows:",
      duplicate_count)

# =====================================================
# 5. INVALID VALUE CHECK
# =====================================================

print("\nChecking invalid measurements...")

invalid_report = pd.DataFrame([
    {
        "check": "Negative mean values",
        "count": (df["mean"] < 0).sum()
    },
    {
        "check": "Negative minimum values",
        "count": (df["min"] < 0).sum()
    },
    {
        "check": "Negative maximum values",
        "count": (df["max"] < 0).sum()
    },
    {
        "check": "Non-positive observation counts",
        "count": (df["n"] <= 0).sum()
    },
    {
        "check": "Minimum greater than maximum",
        "count": (df["min"] > df["max"]).sum()
    },
    {
        "check": "Mean outside min-max range",
        "count": (
            (df["mean"] < df["min"]) |
            (df["mean"] > df["max"])
        ).sum()
    }
])

invalid_report.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "invalid_measurements_report.csv"
    ),
    index=False
)

print(invalid_report.to_string(index=False))

# =====================================================
# 6. STATION AND POLLUTANT COVERAGE
# =====================================================

print("\nChecking station-level pollutant coverage...")

coverage = (
    df.groupby([
        "selected_city",
        "station_id",
        "station_name",
        "parameter_name"
    ])
    .agg(
        records=("period_start", "count"),
        unique_dates=("period_start", "nunique"),
        first_date=("period_start", "min"),
        last_date=("period_start", "max"),
        total_observations=("n", "sum"),
        avg_daily_mean=("mean", "mean")
    )
    .reset_index()
)

coverage["expected_dates"] = 31

coverage["missing_dates"] = (
    coverage["expected_dates"] -
    coverage["unique_dates"]
)

coverage["coverage_status"] = coverage[
    "unique_dates"
].apply(
    lambda x: "Complete" if x == 31 else "Incomplete"
)

coverage.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "station_pollutant_coverage.csv"
    ),
    index=False
)

# =====================================================
# 7. CITY-WISE COVERAGE SUMMARY
# =====================================================

print("\nGenerating city-wise coverage summary...")

city_summary = (
    coverage.groupby([
        "selected_city",
        "parameter_name"
    ])
    .agg(
        station_count=("station_id", "nunique"),
        total_records=("records", "sum"),
        total_unique_station_dates=("unique_dates", "sum"),
        complete_station_count=(
            "coverage_status",
            lambda x: (x == "Complete").sum()
        ),
        incomplete_station_count=(
            "coverage_status",
            lambda x: (x == "Incomplete").sum()
        ),
        avg_daily_mean=("avg_daily_mean", "mean")
    )
    .reset_index()
)

city_summary.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "city_pollutant_coverage_summary.csv"
    ),
    index=False
)

print(city_summary.to_string(index=False))

# =====================================================
# 8. STATION-LEVEL COMBINED POLLUTANT CHECK
# =====================================================

print("\nChecking both pollutant availability...")

station_pollutants = (
    df.groupby([
        "selected_city",
        "station_id",
        "station_name"
    ])["parameter_name"]
    .agg(lambda x: sorted(set(x.dropna())))
    .reset_index(name="available_pollutants")
)

station_pollutants["has_both_pollutants"] = (
    station_pollutants["available_pollutants"]
    .apply(
        lambda x: "PM2.5" in x and "PM10" in x
    )
)

station_pollutants.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "station_pollutant_availability.csv"
    ),
    index=False
)

# =====================================================
# 9. OVERALL QUALITY SUMMARY
# =====================================================

print("\n" + "=" * 55)
print("AIRSCOPE DATA QUALITY SUMMARY")
print("=" * 55)

print("Total measurement rows:", len(df))

print(
    "Unique stations:",
    df["station_id"].nunique()
)

print(
    "Unique cities:",
    df["selected_city"].nunique()
)

print(
    "Unique pollutants:",
    df["parameter_name"].nunique()
)

print(
    "Duplicate records:",
    duplicate_count
)

print(
    "Rows with missing required values:",
    df[important_columns].isna().any(axis=1).sum()
)

print(
    "Stations with both pollutants:",
    station_pollutants[
        "has_both_pollutants"
    ].sum()
)

print(
    "Complete station-pollutant combinations:",
    (coverage["coverage_status"] == "Complete").sum()
)

print(
    "Incomplete station-pollutant combinations:",
    (coverage["coverage_status"] == "Incomplete").sum()
)

print("\nAll quality reports saved successfully.")

print("\nScript 11 completed.")
