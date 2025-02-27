from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
import os
from django.conf import settings
import traceback


def select_groups(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')

@csrf_exempt
def generate_report(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        selected_columns = data.get('selected_columns')
        print(f"Frontend Selected Columns (Backend): {selected_columns}")

        # Run the command to generate the report based on selected columns
        try:
            # Serialize selected_columns to a JSON string
            columns_json_str = json.dumps(selected_columns)

            # Define a path to save the report in the static files directory
            static_report_path = os.path.join(settings.BASE_DIR, 'EssentialAnatomy', 'static', 'survey_report_combined.pdf')

            # Call the management command with the serialized JSON string
            call_command('generate_report', '--columns', columns_json_str)

            # Move the generated report to the static folder for easy download
            if os.path.exists("survey_report_combined.pdf"):
                if os.path.exists(static_report_path):
                    os.remove(static_report_path)  # Remove the existing file if it already exists
                os.rename("survey_report_combined.pdf", static_report_path)

            # Return a response that contains a link to download the generated PDF
            response_data = {'download_url': settings.STATIC_URL + 'survey_report_combined.pdf'}
            return JsonResponse(response_data)

        except Exception as e:
            # Print the full traceback to get more details about the error
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=400)
