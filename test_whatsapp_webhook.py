import json
import time
import requests


def get_test_payload(content):
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "923132680496",
                                    "text": {"body": content},
                                    "id": "wamid.TEST_MESSAGE_001",
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


def conversate():
    message_text = input("Enter test message content: ")
    payload = get_test_payload(message_text)

    start_time = time.time()  # Start timer
    response = requests.post(
        "http://localhost:8000/meta-webhook",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
    )
    end_time = time.time()  # End timer

    elapsed_seconds = end_time - start_time

    print(f"Time taken: {elapsed_seconds:.3f} seconds")
    print("Status code:", response.status_code)
    print("Response:", response.json())


def send_test_message():
    while True:
        try:
            conversate()
        except Exception as e:
            print("Error sending test message:", e)


if __name__ == "__main__":
    send_test_message()
