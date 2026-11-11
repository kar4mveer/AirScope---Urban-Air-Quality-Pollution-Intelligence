
import json
from pathlib import Path

PROJECT_PATH = Path(r"F:\Manjeet\DA Projects\AirScope")
RAW_PATH = PROJECT_PATH / "Dataset" / "Raw"

files = ["stations.json", "parameters.json"]

for filename in files:

    file_path = RAW_PATH / filename

    print("\n" + "=" * 60)
    print("FILE:", filename)
    print("=" * 60)

    with open(file_path, "r", encoding="utf-8") as file:
        result = json.load(file)

    meta = result.get("meta", {})
    data = result.get("data", [])

    print("\nMetadata:")
    print(json.dumps(meta, indent=4))

    print("\nData type:", type(data).__name__)

    if isinstance(data, list):

        print("Total records:", len(data))

        print("\nFirst 5 records:")

        for record in data[:5]:
            print(json.dumps(record, indent=4))

    elif isinstance(data, dict):

        print("Data keys:", list(data.keys()))

        print("\nData preview:")
        print(json.dumps(data, indent=4)[:3000])

    else:
        print("Data preview:")
        print(data)

print("\nInspection completed.")
