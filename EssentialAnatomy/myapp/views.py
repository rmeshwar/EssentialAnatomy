from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
import os
from django.conf import settings
import traceback
from myapp.models import ProcessedResponseAnatomy, ProcessedResponseClinician


def home(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')

def generate(request):
    return render(request, 'generate.html')

@csrf_exempt
def generate_report_view(request):
    if request.method == "POST":
        try:
            form_data = json.loads(request.body)
            # Convert form_data to a JSON string for the management command
            data_str = json.dumps(form_data)

            # Name of the output file
            static_report_path = os.path.join(settings.BASE_DIR, 'EssentialAnatomy', 'static', 'survey_report_combined.pdf')

            # Call the management command with --data
            call_command('generate_report', f'--data={data_str}')

            # Return download link
            download_url = settings.STATIC_URL + 'survey_report_combined.pdf'
            return JsonResponse({"download_url": download_url})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method."}, status=400)

def get_filtered_disciplines(request):
    """
    Retrieves only disciplines that have processed responses in the database.
    """
    # Query distinct professional health programs from processed response tables
    anatomist_programs = ProcessedResponseAnatomy.objects.values_list('professional_health_program', flat=True).distinct()
    clinician_programs = ProcessedResponseClinician.objects.values_list('professional_health_program', flat=True).distinct()

    # Build the response structure
    response_data = {
        "Anatomist": list(anatomist_programs),
        "Clinician": list(clinician_programs)
    }


    return JsonResponse(response_data)