# # reset.py
# from sqlalchemy import create_engine
# from app.database import Base  # adjust this import

# DATABASE_URL = "postgresql://neondb_owner:npg_XWnyZ3D7uJeQ@ep-raspy-sky-a8b6se4f-pooler.eastus2.azure.neon.tech/neondb?sslmode=require"
# # Create engine
# engine = create_engine(DATABASE_URL)

# def reset_database():
#     print("⚠️ Dropping all tables...")
#     Base.metadata.drop_all(bind=engine)

#     # print("✅ Recreating all tables...")
#     # Base.metadata.create_all(bind=engine)

#     # print("🎉 Database reset complete.")

# if __name__ == "__main__":
#     reset_database()

from sqlalchemy import text
from app.database import engine

tables = ["sessions", "messages"]

with engine.begin() as conn:
    for table in tables:
        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))

print("Tables dropped successfully.")
