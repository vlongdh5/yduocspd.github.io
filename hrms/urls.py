from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('attendance/', include('attendance.urls')),
    path('explanations/', include('explanations.urls')),
    path('employees/', include('employees.urls')),
    path('reports/', include('reports.urls')),
    path('', lambda request: redirect('attendance:my_attendance'), name='home'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
