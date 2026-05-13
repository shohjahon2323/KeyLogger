from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Installer


@dataclass(frozen=True)
class InstallerDiskFile:
    relative_path: str
    display_name: str
    kind: str
    size_bytes: int
    modified_at: datetime


def _iter_installer_files(base_dir: Path) -> list[InstallerDiskFile]:
    if not base_dir.exists():
        return []

    out: list[InstallerDiskFile] = []
    for p in base_dir.rglob("*"):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext not in {".exe", ".msi", ".msix", ".inf", ".iso"}:
            continue

        stat = p.stat()
        rel = str(p.relative_to(base_dir)).replace("\\", "/")
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone())
        kind = ext.lstrip(".")
        out.append(
            InstallerDiskFile(
                relative_path=rel,
                display_name=p.name,
                kind=kind,
                size_bytes=int(stat.st_size),
                modified_at=mtime,
            )
        )
    return out


def installers_base_dir() -> Path:
    base = getattr(settings, "INSTALLERS_DIR", None)
    if base is None:
        return Path(settings.BASE_DIR) / "installers"
    return Path(base)


@transaction.atomic
def sync_installers_from_disk() -> int:
    """
    Ensure every supported installer file in INSTALLERS_DIR exists in DB.
    Returns number of DB rows created.
    """
    base_dir = installers_base_dir()
    base_dir.mkdir(parents=True, exist_ok=True)

    disk_files = _iter_installer_files(base_dir)
    created = 0

    existing = {
        i.relative_path: i
        for i in Installer.objects.select_for_update().all().only(
            "id",
            "relative_path",
            "display_name",
            "kind",
            "file_size_bytes",
            "file_modified_at",
        )
    }

    now = timezone.now()
    disk_paths = {f.relative_path for f in disk_files}

    for f in disk_files:
        row = existing.get(f.relative_path)
        if row is None:
            Installer.objects.create(
                relative_path=f.relative_path,
                display_name=f.display_name,
                kind=f.kind,
                file_size_bytes=f.size_bytes,
                file_modified_at=f.modified_at,
                added_at=now,
            )
            created += 1
        else:
            changed = (
                row.display_name != f.display_name
                or row.kind != f.kind
                or row.file_size_bytes != f.size_bytes
                or row.file_modified_at != f.modified_at
            )
            if changed:
                Installer.objects.filter(pk=row.pk).update(
                    display_name=f.display_name,
                    kind=f.kind,
                    file_size_bytes=f.size_bytes,
                    file_modified_at=f.modified_at,
                )

    # Diskda yo'q fayllarni bazadan ham o'chirish
    stale_paths = set(existing.keys()) - disk_paths
    if stale_paths:
        Installer.objects.filter(relative_path__in=stale_paths).delete()

    return created


def resolve_installer_path(installer: Installer) -> Path:
    base_dir = installers_base_dir()
    return base_dir / Path(installer.relative_path)

