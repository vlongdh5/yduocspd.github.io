from django.urls import path
from . import views

app_name = 'employees'

urlpatterns = [
    path('', views.employee_list, name='list'),
    path('create/', views.employee_create, name='create'),
    path('<int:pk>/edit/', views.employee_edit, name='edit'),
    path('<int:pk>/leave/', views.leave_balance_view, name='leave_balance'),
    path('my-leave/', views.MyLeaveView.as_view(), name='my_leave'),
]
