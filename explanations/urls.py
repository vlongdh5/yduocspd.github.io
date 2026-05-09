from django.urls import path
from . import views

app_name = 'explanations'

urlpatterns = [
    path('submit/<int:record_id>/', views.submit_explanation, name='submit'),
    path('my/', views.my_explanations, name='my_explanations'),
    path('pending/', views.pending_approvals, name='pending_approvals'),
    path('review/<int:pk>/', views.review_explanation, name='review'),
    path('bulk-review/', views.bulk_review, name='bulk_review'),
]
