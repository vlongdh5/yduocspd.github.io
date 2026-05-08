from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('otp/verify/', views.OTPVerifyView.as_view(), name='verify_otp'),
    path('otp/setup-totp/', views.SetupTOTPView.as_view(), name='setup_totp'),
]
