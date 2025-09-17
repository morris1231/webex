import os
from flask import Flask, request
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

WEBEX_TOKEN = os.getenv("WEBEX_BOT_TOKEN")
HALO_CLIENT_ID = os.getenv("HALO_CLIENT_ID")
HALO_CLIENT_SECRET = os.getenv("HALO_CLIENT_SECRET")
HALO_API_BASE = os.getenv("HALO_API_BASE")

WEBEX_HEADERS = {
    "Authorization": f"Bearer {WEBEX_TOKEN}",
    "Content-Type": "application/json"
}

def get_halo_access_token():
    """Authenticate with Halo API to get an access token"""
    resp = requests.post(
        f"{HALO_API_BASE}/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": HALO_CLIENT_ID,
            "client_secret": HALO_CLIENT_SECRET,
            "scope": "all",
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def create_halo_ticket(summary, description):
    """Create a ticket in Halo"""
    token = get_halo_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"Summary": summary, "Details": description, "TypeID": 1}  # adjust TypeID!
    resp = requests.post(f"{HALO_API_BASE}/Ticket", json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()

@app.route("/webex", methods=["POST"])
def webex_webhook():
    """Handler for Webex messages"""
    data = request.json
    message_id = data["data"]["id"]

    # fetch full message content
    msg = requests.get(f"https://webexapis.com/v1/messages/{message_id}", headers=WEBEX_HEADERS)
    msg.raise_for_status()
    body = msg.json()
    text = body.get("text", "")
    room_id = body["roomId"]

    if text:
        ticket = create_halo_ticket("Webex Bot Ticket", text)

        # Confirmation back to Webex Space
        conf = f"✅ Halo ticket aangemaakt: {ticket.get('ID', 'onbekend')}"
        requests.post(
            "https://webexapis.com/v1/messages",
            headers=WEBEX_HEADERS,
            json={"roomId": room_id, "text": conf},
        )
        return {"status": "ticket created", "ticket": ticket}, 201

    return {"status": "ignored"}, 200

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5000, debug=True)
