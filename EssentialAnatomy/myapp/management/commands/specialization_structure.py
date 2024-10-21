import json
import os
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Parse Structure.txt and generate a JSON structure with abbreviations based on indentation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='The output path for the JSON file',
            default='parsed_structure_with_abbr.json'  # Default file name
        )

    def handle(self, *args, **kwargs):
        file_path = '/EssentialAnatomy/EssentialAnatomy/data/Structure.txt'  # Update this path to your file location
        output_path = kwargs['output']  # Get output path from arguments

        # Ensure the output is a file, not a directory
        if os.path.isdir(output_path):
            self.stdout.write(self.style.ERROR(f"Output path is a directory. Provide a full file path."))
            return

        # Call the function to generate the structure with abbreviations
        structure = self.generate_structure(file_path)

        # Save the structure as a JSON file
        self.save_json(structure, output_path)

        self.stdout.write(self.style.SUCCESS(f"Structure with abbreviations saved as JSON at {output_path}"))

    def generate_structure(self, file_path):
        structure = {}
        current_group = None
        current_subgroup = None

        with open(file_path, 'r') as file:
            for line in file:
                line = line.rstrip()
                indent_level = line.count("\t")

                if indent_level == 0:  # Group level
                    group_name = line.strip()
                    abbreviation = self.generate_abbr(group_name)
                    structure[group_name] = {"abbr": abbreviation, "subgroups": {}}
                    current_group = structure[group_name]["subgroups"]

                elif indent_level == 1:  # Subgroup level
                    subgroup_name = line.strip()
                    abbreviation = self.generate_abbr(subgroup_name)
                    current_group[subgroup_name] = {"abbr": abbreviation, "specialties": []}
                    current_subgroup = current_group[subgroup_name]["specialties"]

                elif indent_level == 2:  # Specialty level
                    specialty_name = line.strip()
                    abbreviation = self.generate_abbr(specialty_name)
                    current_subgroup.append({"name": specialty_name, "abbr": abbreviation})

        return structure

    def generate_abbr(self, name):
        """Generate an abbreviation by taking the first letter of each word and capitalizing."""
        words = name.split()
        abbreviation = ''.join([word[0].upper() for word in words])[:10]  # Limit abbreviation length
        return abbreviation

    def save_json(self, structure, output_path):
        """Save the parsed structure as a JSON file"""
        with open(output_path, 'w') as json_file:
            json.dump(structure, json_file, indent=4)
