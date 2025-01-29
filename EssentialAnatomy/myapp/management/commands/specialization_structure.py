import json
import os
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Parse Structure.txt and generate a JSON structure with abbreviations based on indentation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='The output path for the JSON file',
            default='parsed_structure.json'  # Default file name
        )

    def handle(self, *args, **kwargs):
        try:
            file_path = staticfiles_storage.path('data/Structure.txt')
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(
                'Structure.txt file not found in static files. Please ensure it is placed in the static/data/ directory.'
            ))
            return
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
        # First, read the file into a list of (indent_level, line_content)
        lines = []
        with open(file_path, 'r') as file:
            for line in file:
                line = line.rstrip('\n')
                indent_level = line.count('\t')
                line_content = line.strip()
                lines.append((indent_level, line_content))

        # Now process the lines
        structure = {}
        stack = []

        for i, (indent_level, line_content) in enumerate(lines):
            abbreviation = self.generate_abbr(line_content)
            node = {'abbr': abbreviation}

            # Adjust stack to current indent level
            while len(stack) > indent_level:
                stack.pop()

            if indent_level == 0:
                # Top-level group
                structure[line_content] = node
                stack = [node]  # Reset stack to current node
            else:
                parent_node = stack[-1]
                # Determine if current node has children by checking next line
                if i + 1 < len(lines) and lines[i + 1][0] > indent_level:
                    # Current node has subgroups
                    if 'subgroups' not in parent_node:
                        parent_node['subgroups'] = {}
                    parent_node['subgroups'][line_content] = node
                else:
                    # Current node is a specialty
                    if 'specialties' not in parent_node:
                        parent_node['specialties'] = []
                    parent_node['specialties'].append({'name': line_content, 'abbr': abbreviation})
            stack.append(node)
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
