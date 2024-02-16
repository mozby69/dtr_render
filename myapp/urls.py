from django.urls import path
from . import views
from .views import index,display_qr_list,webcam_qr_code_scanner,fetch_messages
from .app_views.qr_generator import generate_qr_code
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', index, name="index"),
    path('display_qr_list/', display_qr_list, name='display_qr_list'),
    path('webcam_qr_code_scanner/',webcam_qr_code_scanner,name='webcam_qr_code_scanner'),
    path('fetch_messages/', fetch_messages, name='fetch_messages'),
    path('QR_list/', generate_qr_code, name='generate_qr_code'),
]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
