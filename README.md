# DabaBlane-AI

pip install uv

uv venv
.venv/scripts/activate
uv pip install -r requirements.txt

uvicorn app.main:app --reload




# 🚀 DabaBlane-AI – Live Server Setup Guide

Follow these steps to host the WhatsApp AI assistant server live using **ngrok** and connect it to **Meta for Developers**:

---

## ✅ Prerequisites

* Python installed
* Virtual environment activated (`venv`)
* Required dependencies installed (`pip install -r requirements.txt`)
* Meta for Developer account created

---

## 🛠️ Step-by-Step Setup

### 1. **Install Ngrok**

Go to: [https://ngrok.com/download](https://ngrok.com/download)

Unzip and install `ngrok`, then in your terminal run:

```bash
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
```

> 🔐 Replace `YOUR_NGROK_AUTHTOKEN` with your actual token from [https://dashboard.ngrok.com/get-started/setup](https://dashboard.ngrok.com/get-started/setup) or copy from env

---

### 2. **Start Your FastAPI Server**

Make sure your server is running locally on port **8000**:

```bash
uvicorn app.main:app --reload
```

---

### 3. **Start ngrok Tunnel**

In a **new terminal**, run:

```bash
ngrok http 8000
```

You will get a URL like:

```
https://abcd1234.ngrok.io
```

---

### 4. **Configure Meta Developer Settings**

Go to your app on [https://developers.facebook.com](https://developers.facebook.com), then:

#### ➤ In WhatsApp → Configuration tab:

* **Callback URL:**

  ```
  https://abcd1234.ngrok.io/meta-webhook
  ```

  > (Use the URL from ngrok)

* **Verify Token:**
  Copy the token from your `.env` file:

  ```
  META_VERIFY_TOKEN=my_custom_secret_token
  ```

  Paste this value into the **Verify Token** field.

Click **Verify and Save** ✅

---

### 5. **Set Access Token in Environment**

In your `.env` file, paste your long-lived access token (90 days) from **API Setup** tab:

```
META_ACCESS_TOKEN=EAAXXXXXXX...
META_PHONE_NUMBER_ID=123456789012345
```

> You can generate it from **WhatsApp → API Setup → Temporary token**, and later exchange it for a 90-day token.

---

## 🎉 Your Server Is Live!

Once connected:

* Users can now message your bot on WhatsApp
* Bot will receive messages via `/meta-webhook`
* Responses will be handled automatically based on session and intent

---

## 📩 Troubleshooting

* If messages aren't being received, verify:

  * ngrok tunnel is active
  * Correct callback URL is set in Meta
  * Verify token matches
  * Access token is still valid (check for expiry)

---



start gunicorn

gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000



Dabablane.services

sudo systemctl start dabablane.service

sudo systemctl daemon-reload
sudo systemctl restart dabablane.service
sudo systemctl stop dabablane.service
sudo systemctl enable dabablane.service
sudo systemctl status dabablane.service


LOGS 

journalctl -u dabablane.service -f
