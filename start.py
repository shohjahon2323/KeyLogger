"""
Auto-Start Script — War Room Full Setup
=========================================
Ishlatish:
    python start.py

Bu skript:
1. Django serverni background'da ishga tushiradi
2. Ngrok tunnelni ishga tushiradi
3. Telegram webhook'ni avtomatik o'rnatadi
4. Barcha URL'larni chiqaradi
"""

import subprocess
import sys
import time
import os
import requests
import json

BOT_TOKEN  = '8638904590:AAFHyLPv4NLGopvt0-4L4YktfGt73tjeXY0'
CHAT_ID    = '1844215620'
PORT       = 8080

def get_ngrok_url(retries=10):
    for i in range(retries):
        try:
            r = requests.get('http://localhost:4040/api/tunnels', timeout=3)
            tunnels = r.json().get('tunnels', [])
            for t in tunnels:
                if t.get('public_url', '').startswith('https://'):
                    return t['public_url']
        except Exception:
            pass
        time.sleep(1)
    return None

def set_webhook(ngrok_url):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook'
    r = requests.post(url, json={
        'url': f'{ngrok_url}/bot/webhook/',
        'allowed_updates': ['message', 'callback_query'],
        'drop_pending_updates': True
    })
    return r.json()

def send_startup_message(ngrok_url):
    lines = [
        "<b>WAR ROOM ONLINE</b>",
        "",
        f"Gateway:   <code>{ngrok_url}/</code>",
        f"Instagram: <code>{ngrok_url}/ig/</code>",
        f"Twitter:   <code>{ngrok_url}/tw/</code>",
        f"War Room:  <code>{ngrok_url}/cyber-ops/</code>",
        "",
        "Bot: /start yozing"
    ]
    text = "\n".join(lines)
    requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
        data={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}
    )

def main():
    print("=" * 55)
    print("  WAR ROOM AUTO-START")
    print("=" * 55)

    # 1. Start Django server
    print("[1] Starting Django server on port", PORT)
    django = subprocess.Popen(
        [sys.executable, 'manage.py', 'runserver', f'0.0.0.0:{PORT}'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)

    # 2. Start ngrok
    print("[2] Starting ngrok tunnel...")
    ngrok = subprocess.Popen(
        ['ngrok', 'http', str(PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(3)

    # 3. Get ngrok URL
    print("[3] Getting ngrok URL...")
    ngrok_url = get_ngrok_url()
    if not ngrok_url:
        print("[!] ERROR: Could not get ngrok URL. Is ngrok installed?")
        print("    Run manually: ngrok http 8080")
        print("    Then run:     python setup_bot.py")
        return

    print(f"    URL: {ngrok_url}")

    # Auto-update settings.py NGROK_URL
    try:
        settings_path = os.path.join(os.path.dirname(__file__), 'config', 'settings.py')
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings_content = f.read()
        import re
        settings_content = re.sub(
            r"NGROK_URL\s*=\s*'[^']*'",
            f"NGROK_URL = '{ngrok_url}'",
            settings_content
        )
        with open(settings_path, 'w', encoding='utf-8') as f:
            f.write(settings_content)
        print("    settings.py NGROK_URL updated!")
    except Exception as e:
        print(f"    Could not update settings.py: {e}")

    # 4. Set webhook
    print("[4] Setting Telegram webhook...")
    result = set_webhook(ngrok_url)
    if result.get('ok'):
        print("    Webhook set successfully!")
    else:
        print(f"    Webhook error: {result.get('description')}")

    # 5. Send startup notification
    print("[5] Sending startup notification to Telegram...")
    try:
        send_startup_message(ngrok_url)
        print("    Notification sent!")
    except Exception as e:
        print(f"    Could not send notification: {e}")

    # 6. Print summary
    print()
    print("=" * 55)
    print("  ALL SYSTEMS ONLINE")
    print("=" * 55)
    print(f"  Gateway:   {ngrok_url}/")
    print(f"  Instagram: {ngrok_url}/ig/")
    print(f"  Twitter:   {ngrok_url}/tw/")
    print(f"  War Room:  {ngrok_url}/cyber-ops/")
    print(f"  Bot webhook: {ngrok_url}/bot/webhook/")
    print()
    print("  Telegram botingizga /start yozing!")
    print("=" * 55)
    print()
    print("  Press Ctrl+C to stop all services.")
    print()

    try:
        while True:
            time.sleep(5)
            # Monitor server
            if django.poll() is not None:
                print("[!] Django server stopped. Restarting...")
                django = subprocess.Popen(
                    [sys.executable, 'manage.py', 'runserver', f'0.0.0.0:{PORT}'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        django.terminate()
        ngrok.terminate()
        print("[*] All services stopped.")

if __name__ == '__main__':
    main()
