from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('', views.my_attendance, name='my_attendance'),
    path('upload/', views.upload_attendance, name='upload'),
    path('upload/<int:pk>/', views.upload_detail, name='upload_detail'),
]
