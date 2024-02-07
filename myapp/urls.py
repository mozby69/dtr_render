from django.urls import path
from . import views
from .views import index,display_qr_list,webcam_qr_code_scanner,fetch_messages

urlpatterns = [
    path('', index, name="index"),
    path('display_qr_list/', display_qr_list, name='display_qr_list'),
    path('webcam_qr_code_scanner/',webcam_qr_code_scanner,name='webcam_qr_code_scanner'),
    path('fetch_messages/', fetch_messages, name='fetch_messages'),
]
