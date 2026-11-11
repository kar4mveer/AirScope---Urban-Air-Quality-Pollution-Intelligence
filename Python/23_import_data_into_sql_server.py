
import os
import pandas as pd
import pyodbc

# ============================================================
# 1. CONFIGURATION
# ============================================================

PROJECT_PATH = r"F:\Manjeet\DA Projects\AirScope"

DATA_FOLDER = os.path.join(
    PROJECT_PATH,
    "Dataset",
    "Cleaned",
    "Historical_Final",
    "SQL_Ready"
)

SERVER = r"localhost\SQLEXPRESS"
DATABASE = "AirScope"
DRIVER = "ODBC Driver 18 for SQL Server"

# Windows Authentication
CONNECTION_STRING = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

BATCH_SIZE = 5000

# ============================================================
# 2. FILE PATHS
# ============================================================

station_file = os.path.join(
    DATA_FOLDER, "dim_station.csv"
)

date_file = os.path.join(
    DATA_FOLDER, "dim_date.csv"
)

pollutant_file = os.path.join(
    DATA_FOLDER, "dim_pollutant.csv"
)

fact_file = os.path.join(
    DATA_FOLDER, "fact_air_quality_daily.csv"
)

# ============================================================
# 3. LOAD CSV FILES
# ============================================================

print("=" * 65)
print("AIRSCOPE - SQL SERVER DATA IMPORT")
print("=" * 65)

print("\nLoading CSV files...")

stations = pd.read_csv(
    station_file,
    dtype={"station_id": str}
)

dates = pd.read_csv(date_file)

pollutants = pd.read_csv(pollutant_file)

fact = pd.read_csv(fact_file)

print("Station records:", len(stations))
print("Date records:", len(dates))
print("Pollutant records:", len(pollutants))
print("Fact records:", len(fact))

# ============================================================
# 4. PREPARE DATA TYPES
# ============================================================

dates["date"] = pd.to_datetime(
    dates["date"]
).dt.date

dates["is_weekend"] = (
    dates["is_weekend"].astype(bool)
)

fact["is_statistical_outlier"] = (
    fact["is_statistical_outlier"]
    .astype(str)
    .str.strip()
    .str.lower()
    .isin(["true", "1", "yes"])
)

# ============================================================
# 5. CONNECT TO SQL SERVER
# ============================================================

print("\nConnecting to SQL Server...")

connection = pyodbc.connect(
    CONNECTION_STRING,
    autocommit=False
)

cursor = connection.cursor()

print("SQL Server connection successful.")

# ============================================================
# 6. CHECK EXISTING TABLE DATA
# ============================================================

table_names = [
    "dim_station",
    "dim_date",
    "dim_pollutant",
    "fact_air_quality_daily"
]

for table in table_names:

    cursor.execute(
        f"SELECT COUNT(*) FROM dbo.{table}"
    )

    existing_count = cursor.fetchone()[0]

    if existing_count > 0:

        connection.rollback()
        cursor.close()
        connection.close()

        raise RuntimeError(
            f"{table} already contains {existing_count} rows. "
            "Import stopped to prevent duplicate insertion."
        )

# ============================================================
# 7. HELPER FUNCTION FOR BATCH INSERT
# ============================================================

def insert_data(table_name, columns, dataframe):

    column_list = ", ".join(
        f"[{column}]" for column in columns
    )

    placeholders = ", ".join(
        ["?"] * len(columns)
    )

    query = (
        f"INSERT INTO dbo.{table_name} "
        f"({column_list}) "
        f"VALUES ({placeholders})"
    )

    total_rows = len(dataframe)

    print(f"\nImporting {table_name}...")

    cursor.fast_executemany = True

    for start in range(0, total_rows, BATCH_SIZE):

        batch = dataframe.iloc[
            start:start + BATCH_SIZE
        ]

        records = list(
            batch[columns].itertuples(
                index=False,
                name=None
            )
        )

        cursor.executemany(
            query,
            records
        )

        print(
            f"Inserted {min(start + BATCH_SIZE, total_rows)}"
            f" / {total_rows}"
        )

    print(f"{table_name} import completed.")


# ============================================================
# 8. IMPORT DIMENSION TABLES
# ============================================================

try:

    insert_data(
        "dim_station",
        [
            "station_key",
            "station_id",
            "station_name",
            "selected_city"
        ],
        stations
    )

    insert_data(
        "dim_date",
        [
            "date_key",
            "date",
            "year",
            "quarter",
            "month_number",
            "month_name",
            "year_month",
            "day_of_month",
            "day_of_week",
            "day_name",
            "is_weekend"
        ],
        dates
    )

    insert_data(
        "dim_pollutant",
        [
            "pollutant_key",
            "pollutant_name",
            "unit"
        ],
        pollutants
    )

    # ========================================================
    # 9. IMPORT FACT TABLE
    # ========================================================

    insert_data(
        "fact_air_quality_daily",
        [
            "station_key",
            "date_key",
            "pollutant_key",
            "mean",
            "min",
            "max",
            "n",
            "is_statistical_outlier"
        ],
        fact
    )

    # ========================================================
    # 10. COMMIT TRANSACTION
    # ========================================================

    connection.commit()

    print("\nAll records committed successfully.")

except Exception:

    connection.rollback()

    print(
        "\nImport failed. Transaction rolled back."
    )

    raise

finally:

    cursor.close()
    connection.close()

# ============================================================
# 11. VERIFY SQL SERVER RECORD COUNTS
# ============================================================

print("\nVerifying imported records...")

connection = pyodbc.connect(
    CONNECTION_STRING
)

cursor = connection.cursor()

verification_tables = {
    "dim_station": len(stations),
    "dim_date": len(dates),
    "dim_pollutant": len(pollutants),
    "fact_air_quality_daily": len(fact)
}

all_passed = True

print("\n" + "=" * 65)
print("IMPORT VALIDATION REPORT")
print("=" * 65)

for table, expected_count in verification_tables.items():

    cursor.execute(
        f"SELECT COUNT(*) FROM dbo.{table}"
    )

    actual_count = cursor.fetchone()[0]

    status = (
        "PASS"
        if actual_count == expected_count
        else "FAIL"
    )

    if status == "FAIL":
        all_passed = False

    print(
        f"{table}: Expected = {expected_count}, "
        f"Actual = {actual_count}, Status = {status}"
    )

cursor.close()
connection.close()

print("\n" + "=" * 65)

if all_passed:
    print("ALL TABLES IMPORTED AND VERIFIED SUCCESSFULLY.")
else:
    print("SOME VALIDATION CHECKS FAILED.")

print("Script 23 completed.")
