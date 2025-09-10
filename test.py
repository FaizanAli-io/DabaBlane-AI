# import requests

# # Constants
# NOCO_BASE_URL = "https://database.dabablane.com"
# NOCO_API_TOKEN = "PvRd94S5nqUOtplcdu4ZDq-4O45TGuls72CAekYT"

# HEADERS = {
#     "xc-token": NOCO_API_TOKEN,
#     "Accept": "application/json"
# }

# # Table Mapping
# TABLES = {
#     "Booking-Reservation": "mb92g41bhfubow2"
# }


# def fetch_data_and_columns(table_id: str, table_name: str, limit: int = 3):
#     """
#     Fetch sample data and column names from NocoDB table.
#     """
#     url = f"{NOCO_BASE_URL}/api/v2/tables/{table_id}/records?limit={limit}"
#     response = requests.get(url, headers=HEADERS)
#     response.raise_for_status()

#     data = response.json()
#     records = data.get("list", [])

#     print(f"\n===== {table_name} ({table_id}) =====")

#     if not records:
#         print("No data found.")
#         return

#     # Show columns from the first record
#     print("Columns:")
#     for column in records[0].keys():
#         print(f" - {column}")

#     print("\nSample Data:")
#     for record in records:
#         print(record)


# def run_test():
#     for table_name, table_id in TABLES.items():
#         fetch_data_and_columns(table_id, table_name)


# import pymysql

# conn = pymysql.connect(
#     host='localhost',
#     user='root',
#     password='bilal',  # try '' if not sure
#     database='mysql'  # system database
# )

# print("✅ Connected!")
# conn.close()


# # Entry point
# # if __name__ == "__main__":
# #     #run_test()

import os
import requests
from dotenv import load_dotenv

load_dotenv()
# NOCO_API_TOKEN = os.getenv("NOCO_API_TOKEN")  # directly load the token
# HEADERS = {
#     "xc-token": NOCO_API_TOKEN
# }
# NOCO_BASE_URL = os.getenv("NOCO_BASE_URL")
# NOCO_EMAIL = os.getenv("NOCO_EMAIL")
# NOCO_PASSWORD = os.getenv("NOCO_PASSWORD")

# def get_token():
#     if NOCO_API_TOKEN:
#       return NOCO_API_TOKEN  # Use static token


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

SQLALCHEMY_DATABASE_URL = "postgresql://neondb_owner:npg_XWnyZ3D7uJeQ@ep-raspy-sky-a8b6se4f-pooler.eastus2.azure.neon.tech/neondb?sslmode=require"  # or hardcode if needed
print("DATABASE_URL:", SQLALCHEMY_DATABASE_URL)
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

from fastapi import Depends


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
