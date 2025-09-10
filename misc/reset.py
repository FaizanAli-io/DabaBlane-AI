from sqlalchemy import text
from app.database import engine

tables = ["sessions", "messages"]

with engine.begin() as conn:
    for table in tables:
        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))

print("Tables dropped successfully.")
