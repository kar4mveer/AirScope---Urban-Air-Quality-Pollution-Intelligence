
import os
import pandas as pd

project_path = r"F:\Manjeet\DA Projects\AirScope"

input_file = os.path.join(
    project_path,
    "Dataset", "Raw",
    "all_cities_january_2024_pilot.csv"
)

output_file = os.path.join(
    project_path,
    "Dataset", "Raw",
    "anomalous_measurements.csv"
)

df = pd.read_csv(input_file)

anomalies = df[
    (df["mean"] < df["min"]) |
    (df["mean"] > df["max"])
].copy()

columns = [
    "selected_city",
    "station_id",
    "station_name",
    "parameter_name",
    "period_start",
    "mean",
    "min",
    "max",
    "n",
    "unit"
]

print("\nANOMALOUS MEASUREMENTS")
print("=" * 65)

print(anomalies[columns].to_string(index=False))

anomalies[columns].to_csv(
    output_file,
    index=False
)

print("\nTotal anomalies:", len(anomalies))
print("Saved to:", output_file)
