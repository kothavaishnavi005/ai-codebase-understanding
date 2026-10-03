from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Main Frontend
    path('', views.index_view, name='index'),
    
    # API Endpoints
    path('api/ingest', views.api_ingest, name='api_ingest'),
    path('api/chat', views.api_chat, name='api_chat'),
    path('api/status', views.api_status, name='api_status'),
    path('api/explain-code', views.api_explain_code, name='api_explain_code'),
]
