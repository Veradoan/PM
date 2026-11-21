from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .api_views import LoginAPIView, MeAPIView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='api_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    path('me/', MeAPIView.as_view(), name='api_me'),
]
