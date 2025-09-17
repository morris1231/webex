import os
from flask import Flask, request
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# --- ENV Variables ---
WEBEX_TOKEN = os.getenv("WEBEX_BOT_TOKEN")

HALO_CLIENT_ID = os.getenv("HALO_CLIENT_ID")
HALO_CLIENT_SECRET = os.getenv("HALO_CLIENT_SECRET")
HALO_API_BASE = os.getenv("HALO_API_BASE")     # e.g. https://bncuat.halopsa.com/api
HALO_AUTH_URL = os.getenv("HALO_AUTH_URL")    # e.g. https://bncuat.halopsa.com/auth

# --- Headers ---
WEBEX_HEADERS = {
    "Authorization": f"Bearer {WEBEX_TOKEN}",
    "Content-Type": "application/json"
}


def get_halo_access_token():
    """Authenticate with Halo API to get an access token from /auth"""
    resp = requests.post(
        HALO_AUTH_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": HALO_CLIENT_ID,
            "client_secret": HALO_CLIENT_SECRET,
            "scope": "all",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    print("🔑 Halo token response:", data, flush=True)
    return data["access_token"]


def create_halo_ticket(summary, description):
    """Create a ticket in Halo"""
    token = get_halo_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "Summary": summary,
        "Details": description,
        "TypeID": 1  # ✅ adjust to match a valid TypeID in your Halo config
    }
    resp = requests.post(f"{HALO_API_BASE}/Ticket", json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    print("🎫 Halo ticket response:", data, flush=True)
    return data


@app.route("/webex", methods=["POST"])
def webex_webhook():
    """Handler for Webex Webhook -> Halo Ticket"""
    data = request.json
    print("🚀 Webex webhook payload:", data, flush=True)

    message_id = data["data"]["id"]

    # Fetch full message text from Webex
    msg = requests.get(f"https://webexapis.com/v1/messages/{message_id}", headers=WEBEX_HEADERS)
    msg.raise_for_status()
    body = msg.json()
    text = body.get("text", "")
    room_id = body["roomId"]

    if text:
        print("📩 Webex message text:", text, flush=True)
        ticket = create_halo_ticket("Webex Bot Ticket", text)

        # Confirmation back into Webex
        conf = f"✅ Halo ticket aangemaakt: {ticket.get('ID', 'onbekend')}"
        res = requests.post(
            "https://webexapis.com/v1/messages",
            headers=WEBEX_HEADERS,
            json={"roomId": room_id, "text": conf},
        )
        print("📤 Webex response:", res.json(), flush=True)

        return {"status": "ticket created", "ticket": ticket}, 201

    return {"status": "ignored"}, 200


@app.route("/", methods=["GET"])
def health():
    """Health check for Render"""
    return {"status": "ok", "message": "Webex → Halo bot is running!"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
