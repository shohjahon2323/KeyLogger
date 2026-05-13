from django.urls import path

from . import views


app_name = "appcenter"

urlpatterns = [
    path("", views.index, name="index"),
    path("download/<int:installer_id>/", views.download_installer, name="download"),
]

