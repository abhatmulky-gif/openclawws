import requests
import json
import time

# Configurations
RUNPOD_URL = "https://donation-homeless-outstanding-provincial.trycloudflare.com/analyze_alarm"
TELEGRAM_BOT_TOKEN = "8522629311:AAHKEtL9gKtf5AmPe6wa_-Ah5gt0ctRvHBs"
TELEGRAM_CHAT_ID = "7041322342"

def send_telegram_message(text):
    """Send a message to the Telegram chat using the Bot API"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send message to Telegram: {e}")

def generate_storm():
    print("Generating simulated multi-vendor alarm storm...\n")
    
    cisco_alarm = (
        "Mar 31 09:45:01 CSR-Central-1 %LINK-3-UPDOWN: Interface GigabitEthernet0/0/1, changed state to down\n"
        "Mar 31 09:45:01 CSR-Central-1 %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/0/1, changed state to down\n"
        "Mar 31 09:45:02 CSR-Central-1 %LINK-3-UPDOWN: Interface GigabitEthernet0/0/4, changed state to down"
    )
    
    ericsson_alarms = (
        "2026-03-31 09:45:03 ENB-101 MAJOR ALARM 4001: S1 Link Down - Transport Connection Lost\n"
        "2026-03-31 09:45:04 ENB-102 MAJOR ALARM 4001: S1 Link Down - Transport Connection Lost\n"
        "2026-03-31 09:45:05 ENB-103 MAJOR ALARM 4001: S1 Link Down - Transport Connection Lost"
    )
    
    nokia_alarms = (
        "1001 2026-03-31 09:45:06 AirScale-Cell1 CRITICAL BASE STATION FAULT: SCTP Link Down, Transport Failure\n"
        "1002 2026-03-31 09:45:07 AirScale-Cell2 CRITICAL BASE STATION FAULT: SCTP Link Down, Transport Failure"
    )
    
    storm_payload = f"{cisco_alarm}\n{ericsson_alarms}\n{nokia_alarms}"
    
    print("--- RAW ALARMS GENERATED ---")
    print(storm_payload)
    print("-------------------------------------\n")
    
    # 1. Send the incoming alarms to Telegram
    print("[*] Sending Alarms to Telegram Bot...")
    tg_alarm_message = f"🚨 <b>INCOMING ALARM STORM DETECTED</b> 🚨\n\n<pre>{storm_payload}</pre>\n\n<i>⏳ Forwarding to Svaya AI Engine for correlation...</i>"
    send_telegram_message(tg_alarm_message)
    
    # 2. Wait a few seconds to simulate the "after sometime" effect
    print("[*] Simulating AI processing delay...")
    time.sleep(3)
    
    # 3. Call the RunPod API
    print(f"[*] Dispatching to Svaya AI Engine at: {RUNPOD_URL}")
    try:
        response = requests.post(RUNPOD_URL, json={"alarms": [storm_payload]}, timeout=60)
        
        if response.status_code == 200:
            result = response.json().get("analysis", "No analysis found.")
            print("\n==============================")
            print("  SVAYA AI ROOT CAUSE (RCA)   ")
            print("==============================\n")
            print(result)
            
            # 4. Send the RCA to Telegram
            print("\n[*] Sending RCA to Telegram Bot...")
            tg_rca_message = f"✅ <b>SVAYA AI CORRELATION COMPLETE</b> ✅\n\n{result}"
            send_telegram_message(tg_rca_message)
            
            print("\n[*] Done! Check your Telegram chat.")
        else:
            print(f"HTTP Error {response.status_code}: {response.text}")
    
    except Exception as e:
        print(f"[!] Error querying Svaya Backend: {e}")
        send_telegram_message(f"❌ <b>Svaya AI Engine Error:</b> Could not reach RunPod backend. {e}")

if __name__ == "__main__":
    generate_storm()
