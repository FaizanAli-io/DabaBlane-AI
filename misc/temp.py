import httpx

BASE_URL = "https://api.dabablane.com/api/back/v1/blanes"
TOKEN = "Bearer 422|P58kE87GC5Kgs9UezB1N3SKzznMaqhwmnqE2uDcp570d2070"


def get_online_or_partiel_ids():
    headers = {"Authorization": TOKEN, "Content-Type": "application/json"}

    matching_ids = []
    for page in range(1, 13):
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
