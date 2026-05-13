from django.db import models

class Installer(models.Model):
    class Kind(models.TextChoices):
        EXE = "exe", "EXE"
        MSI = "msi", "MSI"
        MSIX = "msix", "MSIX"
        INF = "inf", "INF"
        ISO = "iso", "ISO"

    relative_path = models.CharField(max_length=500, unique=True)
    display_name = models.CharField(max_length=255)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.EXE)
    file_size_bytes = models.BigIntegerField(default=0)
    file_modified_at = models.DateTimeField()

    added_at = models.DateTimeField(auto_now_add=True)
    download_count = models.BigIntegerField(default=0)

    class Meta:
        ordering = ["-added_at", "display_name"]

    def __str__(self) -> str:
        return self.display_name
