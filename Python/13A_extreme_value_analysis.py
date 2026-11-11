
import os
import pandas as pd

# =====================================================
# 1. CONFIGURATION
# =====================================================

PROJECT_PATH = r"F:\Manjeet\DA Projects\AirScope"

INPUT_FILE = os.path.join(
    PROJECT_PATH,
    "Dataset", "Cleaned",
    "airscope_january_2024_cleaned.csv"
)

OUTPUT_FOLDER = os.path.join(
    PROJECT_PATH,
    "Dataset", "Cleaned", "EDA_Results"
)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# =====================================================
# 2. LOAD DATA
# =====================================================

print("\nLoading January 2024 dataset...")

df = pd.read_csv(INPUT_FILE)

df["period_start"] = pd.to_datetime(
    df["period_start"]
)

print("Total records:", len(df))

# =====================================================
# 3. STATISTICAL OUTLIER ANALYSIS
# =====================================================

print("\n1. STATISTICAL OUTLIER ANALYSIS")

# Calculate IQR separately for each pollutant
# This identifies unusually high daily means.

outlier_frames = []

for pollutant in ["PM2.5", "PM10"]:

    subset = df[
        df["parameter_name"] == pollutant
    ].copy()

    q1 = subset["mean"].quantile(0.25)
    q3 = subset["mean"].quantile(0.75)

    iqr = q3 - q1

    upper_limit = q3 + (1.5 * iqr)
    lower_limit = q1 - (1.5 * iqr)

    subset["q1"] = q1
    subset["q3"] = q3
    subset["iqr"] = iqr
    subset["lower_limit"] = lower_limit
    subset["upper_limit"] = upper_limit

    subset["outlier_flag"] = (
        (subset["mean"] < lower_limit) |
        (subset["mean"] > upper_limit)
    )

    outlier_frames.append(subset)

outliers = pd.concat(
    outlier_frames,
    ignore_index=True
)

outliers = outliers[
    outliers["outlier_flag"]
].copy()

outliers.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "statistical_outliers.csv"
    ),
    index=False
)

print("Statistical outlier records:", len(outliers))

print(
    outliers.groupby("parameter_name").size()
)

# =====================================================
# 4. EXTREME DAILY VALUES
# =====================================================

print("\n2. EXTREME DAILY VALUES")

extreme_values = df[
    (df["mean"] >= 300) |
    (df["max"] >= 900)
].copy()

extreme_values = extreme_values.sort_values(
    "max",
    ascending=False
)

extreme_values.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "extreme_measurement_values.csv"
    ),
    index=False
)

print("Records meeting investigation thresholds:",
      len(extreme_values))

print(
    extreme_values[
        [
            "selected_city",
            "station_id",
            "station_name",
            "parameter_name",
            "period_start",
            "mean",
            "min",
            "max",
            "n"
        ]
    ].head(20).to_string(index=False)
)

# =====================================================
# 5. REPEATED MAXIMUM VALUES
# =====================================================

print("\n3. REPEATED MAXIMUM VALUE CHECK")

repeated_maximums = (
    df.groupby([
        "station_id",
        "station_name",
        "parameter_name",
        "max"
    ])
    .agg(
        repeated_days=("period_start", "nunique"),
        first_date=("period_start", "min"),
        last_date=("period_start", "max")
    )
    .reset_index()
)

repeated_maximums = repeated_maximums[
    repeated_maximums["repeated_days"] >= 3
].sort_values(
    "repeated_days",
    ascending=False
)

repeated_maximums.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "repeated_maximum_values.csv"
    ),
    index=False
)

print(
    "Repeated maximum-value groups:",
    len(repeated_maximums)
)

print(repeated_maximums.head(20).to_string(index=False))

# =====================================================
# 6. STATION-WISE EXTREME VALUE SUMMARY
# =====================================================

print("\n4. STATION-WISE EXTREME VALUE SUMMARY")

station_extremes = (
    df.groupby([
        "selected_city",
        "station_id",
        "station_name",
        "parameter_name"
    ])
    .agg(
        average_mean=("mean", "mean"),
        highest_daily_mean=("mean", "max"),
        highest_recorded_max=("max", "max"),
        reporting_days=("period_start", "nunique"),
        total_observations=("n", "sum")
    )
    .reset_index()
)

station_extremes.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "station_extreme_value_summary.csv"
    ),
    index=False
)

# =====================================================
# 7. CITY-WISE OUTLIER SUMMARY
# =====================================================

print("\n5. CITY-WISE OUTLIER SUMMARY")

city_outlier_summary = (
    outliers.groupby([
        "selected_city",
        "parameter_name"
    ])
    .agg(
        outlier_records=("mean", "count"),
        average_outlier_mean=("mean", "mean"),
        highest_outlier_mean=("mean", "max")
    )
    .reset_index()
)

city_outlier_summary.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "city_outlier_summary.csv"
    ),
    index=False
)

print(city_outlier_summary.to_string(index=False))

# =====================================================
# 8. FINAL SUMMARY
# =====================================================

print("\n" + "=" * 60)
print("AIRSCOPE EXTREME VALUE INVESTIGATION")
print("=" * 60)

print("Total original records:", len(df))

print("Statistical outliers:", len(outliers))

print("Extreme-value investigation records:",
      len(extreme_values))

print("Repeated maximum-value groups:",
      len(repeated_maximums))

print("\nOutput files saved in:")
print(OUTPUT_FOLDER)

print("\nScript 13A completed.")
