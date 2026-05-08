from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('calculate/', views.calculate_view, name='calculate'),
]
