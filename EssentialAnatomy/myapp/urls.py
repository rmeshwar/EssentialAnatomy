from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.home, name='home'),  # URL for selecting groups
    path('about/', views.about, name='about'),
    path('generate/', views.generate, name='generate'),
    path('generate-report/', views.generate_report, name='generate_report'),  # Endpoint for generating the report
]
