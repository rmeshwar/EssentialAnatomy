import pandas as pd
from django.core.management.base import BaseCommand
from myapp.models import Section, Subsection, Topic, Element, ResponseTopic

class Command(BaseCommand):
    help = 'Import structure from Excel file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the Excel file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']
        structure = self.read_excel_structure(file_path)

        for section_name, subsections in structure.items():
            section, created = Section.objects.get_or_create(name=section_name)

            for subsection_name, topics in subsections.items():
                subsection, created = Subsection.objects.get_or_create(section=section, name=subsection_name)

                for topic_name, elements in topics.items():
                    topic, created = Topic.objects.get_or_create(subsection=subsection, name=topic_name)

                    for element_name in elements:
                        Element.objects.get_or_create(topic=topic, name=element_name)

        self.stdout.write(self.style.SUCCESS('Successfully imported structure'))

        self.create_response_topics(structure)

    def read_excel_structure(self, file_path):
        df = pd.read_excel(file_path, engine='openpyxl', header=None)
        structure = {}

        for col in df.columns:
            section = df.iloc[0, col]
            subsection = df.iloc[1, col]
            topic = df.iloc[2, col]
            element = df.iloc[3, col]

            if section not in structure:
                structure[section] = {}

            if subsection not in structure[section]:
                structure[section][subsection] = {}

            if topic not in structure[section][subsection]:
                structure[section][subsection][topic] = []

            if pd.notna(element):
                structure[section][subsection][topic].append(element)

        return structure

    def create_response_topics(self, structure):
        for section_name, subsections in structure.items():
            for subsection_name, topics in subsections.items():
                for topic_name, elements in topics.items():
                    topic = Topic.objects.get(subsection__section__name=section_name, subsection__name=subsection_name, name=topic_name)

                    if elements:
                        for element_name in elements:
                            element = Element.objects.get(topic=topic, name=element_name)
                            ResponseTopic.objects.get_or_create(name=element_name, is_element=True, element=element)
                    else:
                        ResponseTopic.objects.get_or_create(name=topic_name, is_element=False, topic=topic)
