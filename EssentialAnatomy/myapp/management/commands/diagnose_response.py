# myapp/management/commands/diagnose_subsubgroup.py

from django.core.management.base import BaseCommand
from myapp.models import SubSubgroupResponse
from django.db.models import Avg

class Command(BaseCommand):
    help = 'Diagnose subsubgroup responses for a specific subsubgroup_id'

    def add_arguments(self, parser):
        parser.add_argument('subsubgroup_id', type=int, help='ID of the subsubgroup to diagnose')

    def handle(self, *args, **kwargs):
        subsubgroup_id = kwargs['subsubgroup_id']
        responses = SubSubgroupResponse.objects.filter(subsubgroup_id=subsubgroup_id)

        print(f"Responses for subsubgroup_id {subsubgroup_id}:")
        for response in responses:
            print(f"Responder ID: {response.responder_id}, Rating: {response.rating}")

        average_rating = responses.aggregate(average=Avg('rating'))['average']
        print(f"Calculated average rating: {average_rating}")
