
import os
import pandas as pd
import matplotlib.pyplot as plt

# =====================================================
# 1. PROJECT CONFIGURATION
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

print("\nLoading cleaned AirScope dataset...")

df = pd.read_csv(INPUT_FILE)

df["period_start"] = pd.to_datetime(
    df["period_start"]
)

print("Total records:", len(df))
print("Cities:", df["selected_city"].nunique())
print("Stations:", df["station_id"].nunique())

# =====================================================
# 3. CITY-WISE POLLUTION ANALYSIS
# =====================================================

print("\n1. CITY-WISE POLLUTION ANALYSIS")

city_summary = (
    df.groupby([
        "selected_city",
        "parameter_name"
    ])
    .agg(
        average_concentration=("mean", "mean"),
        minimum_concentration=("min", "min"),
        maximum_concentration=("max", "max"),
        total_records=("mean", "count"),
        total_observations=("n", "sum"),
        station_count=("station_id", "nunique")
    )
    .reset_index()
)

city_summary.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "city_pollution_summary.csv"
    ),
    index=False
)

print(city_summary.to_string(index=False))

# =====================================================
# 4. CITY RANKING BY POLLUTANT
# =====================================================

print("\n2. CITY RANKING")

city_ranking = city_summary.copy()

city_ranking["rank"] = (
    city_ranking.groupby("parameter_name")[
        "average_concentration"
    ]
    .rank(method="dense", ascending=False)
    .astype(int)
)

city_ranking = city_ranking.sort_values(
    ["parameter_name", "rank"]
)

city_ranking.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "city_pollution_ranking.csv"
    ),
    index=False
)

print(city_ranking[
    [
        "parameter_name",
        "rank",
        "selected_city",
        "average_concentration"
    ]
].to_string(index=False))

# =====================================================
# 5. STATION-WISE POLLUTION ANALYSIS
# =====================================================

print("\n3. STATION-WISE ANALYSIS")

station_summary = (
    df.groupby([
        "selected_city",
        "station_id",
        "station_name",
        "parameter_name"
    ])
    .agg(
        average_concentration=("mean", "mean"),
        maximum_concentration=("max", "max"),
        minimum_concentration=("min", "min"),
        total_records=("mean", "count"),
        total_observations=("n", "sum")
    )
    .reset_index()
)

station_summary.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "station_pollution_summary.csv"
    ),
    index=False
)

# Top 10 stations per pollutant
top_stations = (
    station_summary.sort_values(
        "average_concentration",
        ascending=False
    )
    .groupby("parameter_name")
    .head(10)
)

top_stations.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "top_10_pollution_stations.csv"
    ),
    index=False
)

print("\nTop 10 stations:")
print(top_stations.to_string(index=False))

# =====================================================
# 6. DAILY POLLUTION TREND
# =====================================================

print("\n4. DAILY POLLUTION TREND")

daily_trend = (
    df.groupby([
        "period_start",
        "selected_city",
        "parameter_name"
    ])
    .agg(
        average_concentration=("mean", "mean"),
        station_count=("station_id", "nunique")
    )
    .reset_index()
)

daily_trend.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "daily_pollution_trend.csv"
    ),
    index=False
)

# =====================================================
# 7. POLLUTANT COMPARISON
# =====================================================

print("\n5. PM2.5 VS PM10 COMPARISON")

pollutant_comparison = (
    df.pivot_table(
        index="selected_city",
        columns="parameter_name",
        values="mean",
        aggfunc="mean"
    )
    .reset_index()
)

if "PM2.5" in pollutant_comparison.columns and \
   "PM10" in pollutant_comparison.columns:

    pollutant_comparison["PM10_PM25_ratio"] = (
        pollutant_comparison["PM10"] /
        pollutant_comparison["PM2.5"]
    )

pollutant_comparison.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "pm25_pm10_comparison.csv"
    ),
    index=False
)

print(pollutant_comparison.to_string(index=False))

# =====================================================
# 8. POLLUTION HOTSPOT ANALYSIS
# =====================================================

print("\n6. POLLUTION HOTSPOT ANALYSIS")

# Define relative ranking within each pollutant.
# These are analytical flags, NOT official AQI categories.

station_summary["pollution_percentile"] = (
    station_summary.groupby("parameter_name")[
        "average_concentration"
    ]
    .rank(pct=True)
)

station_summary["hotspot_flag"] = (
    station_summary["pollution_percentile"] >= 0.90
)

hotspots = station_summary[
    station_summary["hotspot_flag"]
].copy()

hotspots.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "pollution_hotspots.csv"
    ),
    index=False
)

print("Stations in top 10% of average concentration:")
print(hotspots.to_string(index=False))

# =====================================================
# 9. CITY-WISE DAILY DATA COVERAGE
# =====================================================

print("\n7. CITY-WISE DAILY DATA COVERAGE")

coverage_summary = (
    daily_trend.groupby([
        "selected_city",
        "parameter_name"
    ])
    .agg(
        days_with_data=("period_start", "nunique"),
        average_reporting_stations=("station_count", "mean"),
        minimum_reporting_stations=("station_count", "min"),
        maximum_reporting_stations=("station_count", "max")
    )
    .reset_index()
)

coverage_summary.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "daily_station_coverage.csv"
    ),
    index=False
)

print(coverage_summary.to_string(index=False))

# =====================================================
# 10. VISUALISATIONS
# =====================================================

print("\n8. GENERATING VISUALISATIONS")

# City-wise comparison charts
for pollutant in ["PM2.5", "PM10"]:

    plot_data = city_summary[
        city_summary["parameter_name"] == pollutant
    ].sort_values("average_concentration")

    plt.figure(figsize=(10, 6))

    plt.barh(
        plot_data["selected_city"],
        plot_data["average_concentration"]
    )

    plt.title(
        f"Average {pollutant} Concentration by City"
    )

    plt.xlabel("Concentration (µg/m³)")
    plt.ylabel("City")

    plt.tight_layout()

    chart_path = os.path.join(
        OUTPUT_FOLDER,
        f"{pollutant.replace('.', '')}_city_comparison.png"
    )

    plt.savefig(chart_path, dpi=150)
    plt.close()

# Daily trend charts
for pollutant in ["PM2.5", "PM10"]:

    plot_data = daily_trend[
        daily_trend["parameter_name"] == pollutant
    ]

    plt.figure(figsize=(12, 6))

    for city in plot_data["selected_city"].unique():

        city_data = plot_data[
            plot_data["selected_city"] == city
        ]

        plt.plot(
            city_data["period_start"],
            city_data["average_concentration"],
            label=city
        )

    plt.title(
        f"Daily {pollutant} Trend Across Cities"
    )

    plt.xlabel("Date")
    plt.ylabel("Concentration (µg/m³)")
    plt.legend()
    plt.xticks(rotation=45)

    plt.tight_layout()

    chart_path = os.path.join(
        OUTPUT_FOLDER,
        f"{pollutant.replace('.', '')}_daily_trend.png"
    )

    plt.savefig(chart_path, dpi=150)
    plt.close()

# =====================================================
# 11. FINAL SUMMARY
# =====================================================

print("\n" + "=" * 60)
print("AIRSCOPE EDA SUMMARY")
print("=" * 60)

print("Total records:", len(df))
print("Cities analysed:", df["selected_city"].nunique())
print("Stations analysed:", df["station_id"].nunique())

print("\nAverage concentration by city:")
print(city_summary[
    [
        "selected_city",
        "parameter_name",
        "average_concentration"
    ]
].to_string(index=False))

print("\nTotal hotspot station-pollutant combinations:",
      len(hotspots))

print("\nEDA output folder:")
print(OUTPUT_FOLDER)

print("\nScript 13 completed successfully.")
