from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
import os
from django.conf import settings
import traceback


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
