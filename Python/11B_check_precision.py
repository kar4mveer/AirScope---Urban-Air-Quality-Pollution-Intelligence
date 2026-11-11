
import os
import pandas as pd

project_path = r"F:\Manjeet\DA Projects\AirScope"

input_file = os.path.join(
    project_path,
    "Dataset", "Raw",
    "all_cities_january_2024_pilot.csv"
)

df = pd.read_csv(input_file)

anomalies = df[
    (df["mean"] < df["min"]) |
    (df["mean"] > df["max"])
].copy()

pd.set_option("display.precision", 12)

anomalies["mean_minus_min"] = (
    anomalies["mean"] - anomalies["min"]
)

anomalies["mean_minus_max"] = (
    anomalies["mean"] - anomalies["max"]
)

print("\nFULL PRECISION CHECK")
print("=" * 65)

print(
    anomalies[
        [
            "station_id",
            "period_start",
            "mean",
            "min",
            "max",
            "mean_minus_min",
            "mean_minus_max"
        ]
    ].to_string(index=False)
)

# Check using a small numerical tolerance
tolerance = 0.000001

real_anomalies = anomalies[
    (anomalies["mean"] < anomalies["min"] - tolerance) |
    (anomalies["mean"] > anomalies["max"] + tolerance)
]

print("\nOriginal flagged records:", len(anomalies))
print("Records beyond tolerance:", len(real_anomalies))

print("\nPrecision investigation completed.")
