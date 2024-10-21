from django.core.management.base import BaseCommand
from django.db.models import Avg, Count
from myapp.models import SubSubgroupResponseAnatomy, ProcessedResponseAnatomy, ResponseTopic

class Command(BaseCommand):
    help = 'Process survey results and calculate average ratings for each subsubgroup by program category'

    def handle(self, *args, **kwargs):
        # Clear the ProcessedResponseAnatomy table
        ProcessedResponseAnatomy.objects.all().delete()

        # Get all subsubgroup IDs from anatomy topics
        subsubgroup_ids = ResponseTopic.objects.values_list('id', flat=True).order_by('id')

        # Get distinct professional health programs
        programs = SubSubgroupResponseAnatomy.objects.values(
            'responder__professional_health_program'
        ).distinct()

        for subsubgroup_id in subsubgroup_ids:
            self.stdout.write(f"Processing subsubgroup ID: {subsubgroup_id}...")
            for program in programs:
                professional_health_program = program['responder__professional_health_program']

                # Calculate the average rating for this subsubgroup and program
                avg_data = SubSubgroupResponseAnatomy.objects.filter(
                    subsubgroup_id=subsubgroup_id,
                    responder__professional_health_program=professional_health_program
                ).aggregate(avg_rating=Avg('rating'), rating_count=Count('rating'))

                avg_rating = avg_data['avg_rating']
                rating_count = avg_data['rating_count']

                if avg_rating is not None:
                    # Create a new ProcessedResponseAnatomy entry
                    ProcessedResponseAnatomy.objects.create(
                        subsubgroup_id=subsubgroup_id,
                        average_rating=avg_rating,
                        professional_health_program=professional_health_program,
                        rating_count=rating_count
                    )
            self.stdout.write(self.style.SUCCESS(f"Successfully processed subsubgroup ID: {subsubgroup_id}"))

        self.stdout.write(self.style.SUCCESS('Successfully processed anatomist survey results and calculated average ratings by program category'))
