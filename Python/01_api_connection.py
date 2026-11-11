import requests
import getpass
import json

BASE_URL = "https://airquality.xkdr.org/v1"

API_KEY = input("Enter your XKDR API key: ")

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

try:
    response = requests.get(
        f"{BASE_URL}/meta",
        headers=headers,
        timeout=60
    )

    print("Status Code:", response.status_code)

    response.raise_for_status()

    metadata = response.json()

    print("\nAIRSCOPE API CONNECTION SUCCESSFUL")
    print(json.dumps(metadata, indent=4))

except requests.exceptions.RequestException as error:
    print("Connection failed:", error)
