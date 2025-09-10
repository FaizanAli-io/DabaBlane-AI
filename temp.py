# import httpx

# BASE_URL = "https://api.dabablane.com/api/back/v1/blanes"
# TOKEN = "Bearer 422|P58kE87GC5Kgs9UezB1N3SKzznMaqhwmnqE2uDcp570d2070"
# OUTPUT_FILE = "descriptions.txt"

# def get_all_descriptions():
#     descriptions = []
#     headers = {"Authorization": TOKEN, "Content-Type": "application/json"}

#     for page in range(1, 13):  # Loop through all 12 pages
#         try:
#             response = httpx.get(f"{BASE_URL}?page={page}", headers=headers, timeout=20.0)
#             response.raise_for_status()
#             data = response.json().get("data", [])

#             for blane in data:
#                 desc = blane.get("description")
#                 if desc:
#                     descriptions.append(desc.strip())

#             print(f"✅ Page {page} processed ({len(data)} items).")
#         except Exception as e:
#             print(f"❌ Error fetching page {page}: {e}")

#     return descriptions

# if __name__ == "__main__":
#     all_descriptions = get_all_descriptions()
#     with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
#         for desc in all_descriptions:
#             f.write(desc + "\n")

#     print(f"\n💾 Saved {len(all_descriptions)} descriptions to {OUTPUT_FILE}")

import httpx

BASE_URL = "https://api.dabablane.com/api/back/v1/blanes"
TOKEN = "Bearer 422|P58kE87GC5Kgs9UezB1N3SKzznMaqhwmnqE2uDcp570d2070"


def get_online_or_partiel_ids():
    headers = {"Authorization": TOKEN, "Content-Type": "application/json"}

    matching_ids = []
    for page in range(1, 13):  # Loop through all 12 pages
        try:
            response = httpx.get(
                f"{BASE_URL}?page={page}", headers=headers, timeout=20.0
            )
            response.raise_for_status()
            data = response.json().get("data", [])

            for blane in data:
                if blane.get("online") or blane.get("partiel"):
                    matching_ids.append(blane.get("id"))

            print(f"✅ Page {page} processed.")
        except Exception as e:
            print(f"❌ Error fetching page {page}: {e}")

    print("\nIDs with online=True or partiel=True:")
    for blane_id in matching_ids:
        print(blane_id)


if __name__ == "__main__":
    get_online_or_partiel_ids()
