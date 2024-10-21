from django.urls import path
from . import views

urlpatterns = [
    path('select-groups/', views.select_groups, name='select_groups'),  # URL for selecting groups
    path('generate-report/', views.generate_report, name='generate_report'),  # Endpoint for generating the report
]
