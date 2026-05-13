from django.contrib import admin

from .models import Installer


@admin.register(Installer)
class InstallerAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "kind",
        "relative_path",
        "added_at",
        "download_count",
        "file_size_bytes",
        "file_modified_at",
    )
    search_fields = ("display_name", "relative_path")
    list_filter = ("kind", "added_at")
