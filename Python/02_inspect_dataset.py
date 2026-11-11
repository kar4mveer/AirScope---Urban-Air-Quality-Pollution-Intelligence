
import requests
import json
from pathlib import Path

# AirScope - Dataset Inspection

BASE_URL = "https://airquality.xkdr.org/v1"

API_KEY = input("Enter your XKDR API key: ")

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

# Project folders
PROJECT_PATH = Path(r"F:\Manjeet\DA Projects\AirScope")
RAW_PATH = PROJECT_PATH / "Dataset" / "Raw"

RAW_PATH.mkdir(parents=True, exist_ok=True)

endpoints = {
    "stations": "/stations",
    "parameters": "/parameters"
}

for name, endpoint in endpoints.items():

    print(f"\nFetching {name}...")

    try:
        response = requests.get(
            BASE_URL + endpoint,
            headers=headers,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        # Save original API response
        output_file = RAW_PATH / f"{name}.json"

        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

        print(f"{name} retrieved successfully.")
        print("Saved:", output_file)

        # Inspect response structure
        if isinstance(data, dict):
            print("Response keys:", list(data.keys()))

        elif isinstance(data, list):
            print("Total records:", len(data))

        print("\nPreview:")
        print(json.dumps(data, indent=4)[:2000])

    except requests.exceptions.RequestException as error:
        print(f"Error retrieving {name}:", error)

print("\nDataset inspection completed.")
