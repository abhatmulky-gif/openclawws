import requests

BOT_TOKEN = "8662847867:AAENJtmV-8HwGKCRLn8FGOqAdlPevlYV7dU"
CHAT_ID = "7041322342"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {"chat_id": CHAT_ID, "text": f"🚨 **SVAYA RUNPOD ALERT** 🚨\nTesting the connection!", "parse_mode": "Markdown"}

print("Sending to:", url)
try:
    response = requests.post(url, json=payload, timeout=5)
    print("Status:", response.status_code)
    print("Response:", response.text)
except Exception as e:
    print("Error:", e)