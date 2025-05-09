from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from django.db.models import Q
import os
from django.conf import settings
import traceback
from myapp.models import Section, ProcessedResponseAnatomy, ProcessedResponseClinician


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
            print("Exception occurred in generate_report view:")
            traceback.print_exc()  # Logs full traceback to terminal
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

def get_sections_and_subsections(request):
    """
    Returns  {
        "Back": ["Superficial back", "Deep back", …],
        "Upper Limb": ["Pectoral region", "Arm", …],
        …
    }
    """
    data = {}
    for sec in Section.objects.prefetch_related('subsections').all():
        data[sec.name] = [sub.name for sub in sec.subsections.all()]
    return JsonResponse(data)

def get_clinician_specialties(request):
    """
    Returns, for every clinician PHP that already has processed responses,
    the specialties (primary_field) and any subspecialties (subfield) that
    also have data.

    Response shape:
    {
        "Dentistry": {
            "Endodontics": [],
            "Oral and Maxillofacial Surgery": [],
            ...
        },
        "Medicine - Allopathic": {
            "Anesthesiology": ["Pain Medicine", "Pediatric Anesthesiology"],
            ...
        },
        ...
    }
    """
    qs = (ProcessedResponseClinician.objects
          .values('professional_health_program', 'primary_field', 'subfield')
          .distinct())

    result = {}
    for row in qs:
        php = row['professional_health_program']
        primary = row['primary_field']
        sub    = row['subfield']
        if primary is None:
            continue                    # ignore rows that did not record a specialty
        result.setdefault(php, {}).setdefault(primary, set())
        if sub:
            result[php][primary].add(sub)

    # JSON‑serialise: convert sets ➜ sorted lists
    for php in result:
        for prim in result[php]:
            result[php][prim] = sorted(result[php][prim])

    return JsonResponse(result)
