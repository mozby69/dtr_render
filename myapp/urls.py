from django.urls import path
from . import views
from .views import index,display_qr_list,webcam_qr_code_scanner,fetch_messages
from .app_views.qr_generator import generate_qr_code,user_profile
from django.conf.urls.static import static
from django.conf import settings
from .app_views.export import export,export_data_afternoon
from django.contrib.auth import views as auth_views
from django.views.generic.base import TemplateView

urlpatterns = [
    path('', views.login_view, name='login'),
    path('home/', views.home, name='home'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('index/', index, name="index"),
    path('display_qr_list/', display_qr_list, name='display_qr_list'),
    path('webcam_qr_code_scanner/',webcam_qr_code_scanner,name='webcam_qr_code_scanner'),
    path('fetch_messages/', fetch_messages, name='fetch_messages'),
    path('QR_list/', generate_qr_code, name='generate_qr_code'),
    path('user_profile/<int:pk>/', user_profile, name='user_profile'),
    path('export/', export, name='export'),
    path('export_all/', export_data_afternoon, name='export_data_afternoon'),
]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
