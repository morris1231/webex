import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

# Load env vars
load_dotenv()
app = Flask(__name__)

# Webex
WEBEX_TOKEN = os.getenv("WEBEX_BOT_TOKEN")

# Halo
HALO_CLIENT_ID = os.getenv("HALO_CLIENT_ID")
HALO_CLIENT_SECRET = os.getenv("HALO_CLIENT_SECRET")
HALO_API_BASE = os.getenv("HALO_API_BASE")        # e.g. https://bncuat.halopsa.com/api
HALO_AUTH_URL = os.getenv("HALO_AUTH_URL", "")    # optional; if empty → APIKey mode
HALO_AUTH_MODE = os.getenv("HALO_AUTH_MODE", "apikey")  # "oauth" or "apikey"

WEBEX_HEADERS = {
    "Authorization": f"Bearer {WEBEX_TOKEN}",
    "Content-Type": "application/json"
}


def get_halo_headers():
    """Return headers for calling Halo API based on auth mode."""
    if HALO_AUTH_MODE.lower() == "oauth" and HALO_AUTH_URL:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = {
            "grant_type": "client_credentials",
            "client_id": HALO_CLIENT_ID,
            "client_secret": HALO_CLIENT_SECRET,
            "scope": "all"
        }
        resp = requests.post(HALO_AUTH_URL, headers=headers, data=payload)
        print("🔑 Halo auth response:", resp.status_code, resp.text, flush=True)
        resp.raise_for_status()
        try:
            token = resp.json().get("access_token")
            return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        except Exception:
            raise RuntimeError(f"⚠️ Halo auth returned non-JSON: {resp.text}")
    else:
        # APIKey direct mode
        return {"APIKey": HALO_CLIENT_SECRET, "Content-Type": "application/json"}


def create_halo_ticket(summary, description):
    """Create a Halo ticket"""
    headers = get_halo_headers()
    payload = {"Summary": summary, "Details": description, "TypeID": 1}  # adjust TypeID for your config
    resp = requests.post(f"{HALO_API_BASE}/Ticket", headers=headers, json=payload)
    print("🎫 Halo ticket response:", resp.status_code, resp.text, flush=True)
    resp.raise_for_status()
    return resp.json()


@app.route("/webex", methods=["POST"])
def webex_webhook():
    """Handle Webex webhook → create Halo ticket"""
    data = request.json
    print("🚀 Webex webhook payload:", data, flush=True)

    message_id = data.get("data", {}).get("id")
    if not message_id:
        return {"status": "ignored", "reason": "missing message id"}, 400

    # Fetch original Webex message
    msg = requests.get(f"https://webexapis.com/v1/messages/{message_id}", headers=WEBEX_HEADERS)
    msg.raise_for_status()
    body = msg.json()
    text = body.get("text", "")
    room_id = body.get("roomId")

    if not text:
        return {"status": "ignored", "reason": "no text"}, 200

    print("📩 Webex message text:", text, flush=True)

    # Create ticket in Halo
    ticket = create_halo_ticket("Webex Bot Ticket", text)

    # Reply into Webex
    conf_msg = f"✅ Halo ticket aangemaakt met ID: {ticket.get('ID', 'onbekend')}"
    res = requests.post(
        "https://webexapis.com/v1/messages",
        headers=WEBEX_HEADERS,
        json={"roomId": room_id, "text": conf_msg}
    )
    print("📤 Webex reply:", res.status_code, res.text, flush=True)

    return {"status": "ticket created", "halo_ticket": ticket}, 201


@app.route("/", methods=["GET"])
def healthcheck():
    return {"status": "ok", "message": "Webex → Halo bot is running"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
