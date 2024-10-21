from django.core.management.base import BaseCommand
from django.db.models import Avg, Count
from myapp.models import SubSubgroupResponseClinician, ProcessedResponseClinician, ResponseTopic

class Command(BaseCommand):
    help = 'Process clinician survey results and calculate average ratings for each subsubgroup by clinician program category'

    def handle(self, *args, **kwargs):
        # Clear the ProcessedResponseClinician table
        ProcessedResponseClinician.objects.all().delete()

        # Get all subsubgroup IDs from clinician topics
        subsubgroup_ids = ResponseTopic.objects.values_list('id', flat=True).order_by('id')

        # Get distinct professional health programs, primary fields, and subfields
        programs = SubSubgroupResponseClinician.objects.values(
            'responder__professional_health_program',
            'responder__primary_field',
            'responder__subfield'
        ).distinct()

        # Process each subsubgroup and calculate average ratings for each program
        for subsubgroup_id in subsubgroup_ids:
            self.stdout.write(f"Processing subsubgroup ID: {subsubgroup_id}...")
            for program in programs:
                professional_health_program = program['responder__professional_health_program']
                primary_field = program['responder__primary_field']
                subfield = program['responder__subfield']

                # Calculate the average rating for this subsubgroup and program
                queryset = SubSubgroupResponseClinician.objects.filter(
                    subsubgroup_id=subsubgroup_id,
                    responder__professional_health_program=professional_health_program,
                    responder__primary_field=primary_field,
                    responder__subfield=subfield
                )

                avg_rating = queryset.aggregate(Avg('rating'))['rating__avg']
                rating_count = queryset.aggregate(Count('rating'))['rating__count']

                if avg_rating is not None and rating_count > 0:
                    # Create a new ProcessedResponseClinician entry
                    ProcessedResponseClinician.objects.create(
                        subsubgroup_id=subsubgroup_id,
                        average_rating=avg_rating,
                        professional_health_program=professional_health_program,
                        primary_field=primary_field,
                        subfield=subfield,
                        rating_count=rating_count  # Store the count of ratings
                    )

                    self.stdout.write(
                        self.style.SUCCESS(f"Subsubgroup ID: {subsubgroup_id}, Program: {professional_health_program}, "
                                           f"Primary Field: {primary_field}, Subfield: {subfield}, "
                                           f"Average Rating: {avg_rating:.2f}, Rating Count: {rating_count}")
                    )

        self.stdout.write(self.style.SUCCESS('Successfully processed clinician survey results and calculated average ratings by program category'))
