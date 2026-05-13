from __future__ import annotations

from django.db.models import F
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.utils.http import content_disposition_header

from .models import Installer
from .services import resolve_installer_path, sync_installers_from_disk


def index(request):
    sync_installers_from_disk()
    installers = Installer.objects.all()
    return render(request, "appcenter/index.html", {"installers": installers})


def download_installer(request, installer_id: int):
    installer = get_object_or_404(Installer, pk=installer_id)
    path = resolve_installer_path(installer)

    if not path.exists() or not path.is_file():
        raise Http404("File not found on disk")

    Installer.objects.filter(pk=installer.pk).update(download_count=F("download_count") + 1)

    # Fayl kengaytmasiga qarab to'g'ri MIME type belgilash
    MIME_TYPES = {
        "exe":  "application/vnd.microsoft.portable-executable",
        "msi":  "application/x-msi",
        "msix": "application/msix",
        "inf":  "text/plain",
        "iso":  "application/x-iso9660-image",
    }
    mime = MIME_TYPES.get(installer.kind.lower(), "application/octet-stream")

    # Fayl nomini disk dagi haqiqiy nom bilan yuborish (kengaytma bilan)
    filename = path.name  # masalan: "Windows 11 Pro 23H2.iso"

    f = open(path, "rb")
    response = FileResponse(f, content_type=mime, as_attachment=True)
    response["Content-Disposition"] = content_disposition_header(True, filename)
    return response
