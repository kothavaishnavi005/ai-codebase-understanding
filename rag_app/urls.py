from django.urls import path
from . import views

urlpatterns = [
    # Main Frontend
    path('', views.index_view, name='index'),
    
    # API Endpoints
    path('api/ingest', views.api_ingest, name='api_ingest'),
    path('api/chat', views.api_chat, name='api_chat'),
    path('api/status', views.api_status, name='api_status'),
]
