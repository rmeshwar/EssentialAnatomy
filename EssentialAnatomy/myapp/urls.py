from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.select_groups, name='home'),  # URL for selecting groups
    path('generate-report/', views.generate_report, name='generate_report'),  # Endpoint for generating the report
]
