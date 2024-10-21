from django.core.management.base import BaseCommand
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from django.conf import settings
import os
from django.contrib.staticfiles.storage import staticfiles_storage
import json
import shutil
from functools import partial
from myapp.models import (
    Section, Subsection, Element, Topic, ResponseTopic,
    ProcessedResponseAnatomy, ProcessedResponseClinician, ResponderAnatomy, ResponderClinician
)

class Command(BaseCommand):
    help = 'Generate a PDF report of survey results'

    def add_arguments(self, parser):
        parser.add_argument(
            '--categories',
            nargs='+',
            type=str,
            help='Program categories to include in the report (e.g., "Anatomist", "Clinician / Medicine - Allopathic", etc.)',
            required=True
        )

    def handle(self, *args, **kwargs):
        categories = [category.strip() for category in kwargs['categories']]

        # Load parsed_structure.json to handle main groups and subgroups
        try:
            json_file_path = staticfiles_storage.path('data/parsed_structure.json')
            with open(json_file_path, 'r') as f:
                parsed_structure = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(
                f'File not found: {json_file_path}. Please ensure the file exists and is in the correct location.'))
            return

        # Flatten structure to match input categories
        def expand_structure(structure, parent_key='', parent_abbr=''):
            expanded = {}
            abbreviations_map = {}  # Dictionary to map abbreviations to full labels

            for key, value in structure.items():
                current_key = f"{parent_key} / {key}".strip() if parent_key else key
                if parent_abbr:
                    current_abbr = f"{parent_abbr}/{value.get('abbr', key)}"
                else:
                    current_abbr = value.get('abbr', key)

                expanded[current_key] = {"label": key, "abbr": current_abbr}
                abbreviations_map[current_abbr] = current_key  # Map abbreviation to the full label

                if 'subgroups' in value:
                    sub_expanded, sub_abbreviations = expand_structure(value['subgroups'], current_key, current_abbr)
                    expanded.update(sub_expanded)
                    abbreviations_map.update(sub_abbreviations)

                if 'specialties' in value:
                    for specialty in value['specialties']:
                        specialty_key = f"{current_key} / {specialty['name']}".strip()
                        specialty_abbr = f"{current_abbr}/{specialty.get('abbr', specialty['name'])}"
                        expanded[specialty_key] = {"label": specialty['name'], "abbr": specialty_abbr}
                        abbreviations_map[specialty_abbr] = specialty_key

            return expanded, abbreviations_map

        # Expand the parsed structure into a flattened dictionary
        expanded_categories, abbreviations_map = expand_structure(parsed_structure)
        # print(abbreviations_map)

        # Match input categories with the expanded structure
        processed_responses = []
        for category in categories:
            if category in expanded_categories:
                matched_category = expanded_categories[category]
                if "Anatomist" in category:
                    processed_responses.append(
                        {
                            "model": ProcessedResponseAnatomy,
                            "label": matched_category['label'],
                            "full_key": category,  # Store the full hierarchical key
                            "is_anatomist": True,
                            "query": {}
                        }
                    )
                elif category == "Clinician":
                    # For the general Clinician category, include all responses without specific filtering
                    processed_responses.append(
                        {
                            "model": ProcessedResponseClinician,
                            "label": "Clinician",
                            "full_key": category,
                            "is_anatomist": False,
                            "query": {}  # No filter for general clinician category
                        }
                    )
                elif "Clinician" in category:
                    # Split the category to identify whether it's a specific primary field or just the professional health program
                    category_parts = category.split(" / ")
                    if len(category_parts) == 3:
                        # This is for a more specific category that includes a primary field, like "Anesthesiology"
                        professional_health_program = category_parts[1]
                        primary_field = category_parts[2]

                        processed_responses.append(
                            {
                                "model": ProcessedResponseClinician,
                                "label": matched_category['label'],
                                "full_key": category,
                                "is_anatomist": False,
                                "query": {
                                    "professional_health_program": professional_health_program,
                                    "primary_field": primary_field  # Add the primary field filter here
                                }
                            }
                        )
                    else:
                        # For more general clinician categories, without a specific primary field
                        processed_responses.append(
                            {
                                "model": ProcessedResponseClinician,
                                "label": matched_category['label'],
                                "full_key": category,
                                "is_anatomist": False,
                                "query": {
                                    "professional_health_program": matched_category['label']
                                }
                            }
                        )

        if not processed_responses:
            self.stdout.write(self.style.ERROR("No valid categories provided for generating the report."))
            return

        # Generate a single PDF report for the combined responses
        self.generate_pdf_report(processed_responses, expanded_categories, abbreviations_map)

    def generate_pdf_report(self, processed_responses, expanded_categories, abbreviations_map):
        # Load parsed_structure.json to handle main groups and subgroups
        try:
            json_file_path = staticfiles_storage.path('data/parsed_structure.json')
            with open(json_file_path, 'r') as f:
                parsed_structure = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(
                f'File not found: {json_file_path}. Please ensure the file exists and is in the correct location.'))
            return

        def get_color_for_rating(rating):
            """Return a color from red to green based on the rating (1 to 7)."""
            # Normalize the rating to a value between 0 and 1
            normalized = (rating - 1) / 6
            # Interpolate between red (1, 0, 0) and green (0, 1, 0)
            r = 1 - normalized
            g = normalized
            b = 0

            r = (r + 1) / 2
            g = (g + 1) / 2
            b = (b + 1) / 2
            return colors.Color(r, g, b)

        output_file_path = os.path.join(settings.BASE_DIR, 'EssentialAnatomy', 'static', 'survey_report_combined.pdf')
        doc = SimpleDocTemplate(output_file_path, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        blue_text_style = ParagraphStyle(name='BlueText', parent=styles['Heading3'], textColor=colors.blue)

        available_width = letter[0] - 1 * inch  # Total page width minus the margins
        # Adjusted column widths to ensure all fit on the page
        first_col_width = available_width * 0.3  # First column gets 30% of the page width
        remaining_width = available_width - first_col_width
        other_col_width = remaining_width / (len(processed_responses) + 1)  # Divide the rest evenly among categories + total column
        col_widths = [first_col_width] + [other_col_width] * (len(processed_responses) + 1)

        # Extracting abbreviations for categories from parsed_structure.json
        category_abbreviations = {}
        for group in parsed_structure:
            group_data = parsed_structure[group]
            group_abbr = group_data.get('abbr', group)
            category_abbreviations[group] = group_abbr
            if 'subgroups' in group_data:
                for subgroup in group_data['subgroups']:
                    subgroup_data = group_data['subgroups'][subgroup]
                    subgroup_abbr = subgroup_data.get('abbr', subgroup)
                    category_abbreviations[subgroup] = subgroup_abbr
                    if 'specialties' in subgroup_data:
                        for specialty in subgroup_data['specialties']:
                            specialty_name = specialty['name']
                            specialty_abbr = specialty.get('abbr', specialty_name)
                            category_abbreviations[specialty_name] = specialty_abbr

        # Build the report table data
        sections = Section.objects.all()
        section_indices = []
        abbreviations_used = set()

        for section in sections:
            section_title_row = [Paragraph(f"{section.name}", styles['Title'])] + ['' for _ in processed_responses] + ['']
            section_data = [section_title_row]
            section_index = len(section_data)
            section_indices.append(section_index)

            subsection_indices = []

            subsections = Subsection.objects.filter(section=section)
            for subsection in subsections:
                subsection_index = len(section_data)
                subsection_indices.append(subsection_index)

                section_data.append(
                    [Paragraph(f"{subsection.name}", styles['Heading2'])] + ['' for _ in processed_responses] + [''])

                topics = Topic.objects.filter(subsection=subsection)
                for topic in topics:
                    response_topic = ResponseTopic.objects.filter(topic=topic).first()
                    if response_topic:
                        # Collect ratings for each category and calculate total
                        row = [Paragraph(f"{response_topic.name}", styles['Normal'])]
                        total_ratings = []
                        for response in processed_responses:
                            processed_model, query = response['model'], response['query']
                            processed_response_qs = processed_model.objects.filter(subsubgroup_id=response_topic.id,
                                                                                   **query)
                            if processed_response_qs.exists():
                                abbr = expanded_categories[response['full_key']]['abbr']
                                abbreviations_used.add(abbr)

                                # Multiple responses might be found, aggregate their values
                                avg_ratings = []
                                rating_counts = []
                                for processed_response in processed_response_qs:
                                    avg_ratings.append(processed_response.average_rating)
                                    rating_counts.append(processed_response.rating_count)

                                # Calculate the weighted average if multiple records exist
                                total_rating_sum = sum(r * count for r, count in zip(avg_ratings, rating_counts))
                                total_rating_count = sum(rating_counts)
                                if total_rating_count > 0:
                                    rating = total_rating_sum / total_rating_count
                                    row.append(Paragraph(f"{rating:.2f}", styles['Normal']))
                                    total_ratings.append((rating, total_rating_count))
                                else:
                                    row.append(Paragraph("N/A", styles['Normal']))
                            else:
                                row.append(Paragraph("N/A", styles['Normal']))

                        # Calculate total average rating
                        total_sum = sum(rating * count for rating, count in total_ratings)
                        total_count = sum(count for _, count in total_ratings)
                        if total_count > 0:
                            total_average = total_sum / total_count
                            row.append(Paragraph(f"{total_average:.2f}", styles['Normal']))
                        else:
                            row.append(Paragraph("N/A", styles['Normal']))

                        section_data.append(row)
                    else:
                        row = [Paragraph(f"{topic.name}", blue_text_style)]
                        # Add abbreviation and count of responses (n={x})
                        # Define a style for the small, red text
                        small_red_text_style = ParagraphStyle(name='SmallRedText', parent=styles['Normal'],
                                                              textColor=colors.red, fontSize=8)

                        # Modify the logic to include "n={x}" along with the abbreviation
                        for response in processed_responses:
                            abbr = expanded_categories[response['full_key']]['abbr']
                            abbreviations_used.add(abbr)

                            # Calculate the count (number of responses for this category)
                            if response['is_anatomist']:
                                if response['full_key'] == "Anatomist":
                                    # Count all responder entries for Anatomist (broad category)
                                    count = ResponderAnatomy.objects.count()
                                else:
                                    # Count specific to a health program within Anatomist
                                    count = ResponderAnatomy.objects.filter(
                                        professional_health_program=response['label']
                                    ).count()
                            else:
                                if response['full_key'] == "Clinician":
                                    # Count all responder entries for Clinician (broad category)
                                    count = ResponderClinician.objects.count()
                                elif 'primary_field' in response['query']:
                                    # Count for a specific field under Clinician
                                    count = ResponderClinician.objects.filter(
                                        professional_health_program=response['query']['professional_health_program'],
                                        primary_field=response['query']['primary_field']
                                    ).count()
                                else:
                                    # Count for a more specific clinician program without a primary field
                                    count = ResponderClinician.objects.filter(
                                        professional_health_program=response['query'].get('professional_health_program',
                                                                                          response['label'])
                                    ).count()

                            # Format abbreviation with count "n={x}"
                            abbr_with_count = f"{abbr} <font color='red' size='8'>n={count}</font>"
                            row.append(Paragraph(abbr_with_count, styles['Heading3']))
                            abbreviations_used.add(abbr)
                        row.append(Paragraph("Total", styles['Heading3']))
                        section_data.append(row)

                    elements_query = Element.objects.filter(topic=topic)
                    for element in elements_query:
                        responsetopic = ResponseTopic.objects.filter(element=element).first()
                        if responsetopic:
                            row = [Paragraph(f"{element.name}", styles['Normal'])]
                            total_ratings = []
                            for response in processed_responses:
                                processed_model, query = response['model'], response['query']
                                processed_response_qs = processed_model.objects.filter(subsubgroup_id=responsetopic.id,
                                                                                       **query)
                                if processed_response_qs.exists():
                                    avg_ratings = []
                                    rating_counts = []
                                    for processed_response in processed_response_qs:
                                        avg_ratings.append(processed_response.average_rating)
                                        rating_counts.append(processed_response.rating_count)

                                    total_rating_sum = sum(r * count for r, count in zip(avg_ratings, rating_counts))
                                    total_rating_count = sum(rating_counts)
                                    if total_rating_count > 0:
                                        rating = total_rating_sum / total_rating_count
                                        row.append(Paragraph(f"{rating:.2f}", styles['Normal']))
                                        total_ratings.append((rating, total_rating_count))
                                    else:
                                        row.append(Paragraph("N/A", styles['Normal']))
                                else:
                                    row.append(Paragraph("N/A", styles['Normal']))

                            # Calculate total average rating
                            total_sum = sum(rating * count for rating, count in total_ratings)
                            total_count = sum(count for _, count in total_ratings)
                            if total_count > 0:
                                total_average = total_sum / total_count
                                row.append(Paragraph(f"{total_average:.2f}", styles['Normal']))
                            else:
                                row.append(Paragraph("N/A", styles['Normal']))

                            section_data.append(row)

            header = [Paragraph('', styles['Heading3'])] + [
                Paragraph(response['label'], styles['Heading3']) for response in processed_responses] + [
                         Paragraph("Total", styles['Heading3'])]

            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (len(processed_responses) + 1, 0), colors.grey),
                ('BACKGROUND', (0, 1), (len(processed_responses) + 1, 1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (len(processed_responses) + 1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 2), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ])
            for idx in subsection_indices:
                table_style.add('SPAN', (0, idx), (len(processed_responses) + 1, idx))
                table_style.add('BACKGROUND', (0, idx), (len(processed_responses) + 1, idx), colors.lightgrey)

            for idx in section_indices:
                idx -= 1
                table_style.add('SPAN', (0, idx), (len(processed_responses) + 1, idx))
                table_style.add('BACKGROUND', (0, idx), (len(processed_responses) + 1, idx), colors.grey)

            # Add dynamic background colors for rating cells
            for i, row in enumerate(section_data[1:], start=1):  # start=1 to skip the header
                for j, cell in enumerate(row[1:], start=1):  # start=1 to skip the first column
                    if isinstance(cell, Paragraph):
                        try:
                            rating = float(cell.getPlainText())
                            color = get_color_for_rating(rating)
                            table_style.add('BACKGROUND', (j, i), (j, i), color)
                        except ValueError:
                            pass

            t = Table(section_data, colWidths=col_widths)
            t.setStyle(table_style)
            elements.append(t)
            elements.append(Spacer(1, 12))  # Add space between sections

        def add_page_number(canvas, doc, abbreviations_used, abbreviations_map):
            page_num = canvas.getPageNumber()
            text = f"Page {page_num}"

            # Draw the page number in the reserved right margin area
            right_margin_x = 200 * mm  # X position for the page number
            canvas.drawRightString(right_margin_x, 20 * mm, text)

            # Add abbreviation key at the bottom with reserved space on the right
            if abbreviations_used:
                # Create list of abbreviation entries
                abbreviation_entries = []
                for abbr in abbreviations_used:
                    if abbr in abbreviations_map:
                        label = abbreviations_map[abbr]
                        abbreviation_entries.append(f"{abbr}: {label}")
                    else:
                        abbreviation_entries.append(f"{abbr}: Unknown")

                # Define the maximum width for the key text, leaving room for the page number on the right (e.g., reserve 40 mm)
                reserved_space_on_right = 80 * mm
                max_width = (letter[
                                 0] - reserved_space_on_right - 20 * mm)  # Total page width minus reserved space and left margin
                current_line = ""
                lines = []
                space_width = stringWidth(" ", 'Helvetica', 8)

                # Split entries into lines based on available width
                for entry in abbreviation_entries:
                    entry_width = stringWidth(entry, 'Helvetica', 8)
                    if stringWidth(current_line, 'Helvetica', 8) + entry_width + space_width > max_width:
                        lines.append(current_line)
                        current_line = entry
                    else:
                        if current_line:
                            current_line += " | " + entry
                        else:
                            current_line = entry

                # Add the last line if there's remaining text
                if current_line:
                    lines.append(current_line)

                # Draw each line at the bottom, starting from the left
                y_position = 20 * mm
                for line in lines:
                    canvas.drawString(20 * mm, y_position, line)
                    y_position -= 10  # Move up for the next line

                # print(f"Page {page_num} - Abbreviations Used: {abbreviations_used}")
                # print(f"Page {page_num} - Abbreviation Key: {key_text}")

        # Generate PDF with updated function call
        doc.build(elements,
                  onFirstPage=lambda canvas, doc: add_page_number(canvas, doc, abbreviations_used, abbreviations_map),
                  onLaterPages=lambda canvas, doc: add_page_number(canvas, doc, abbreviations_used, abbreviations_map))

        self.stdout.write(self.style.SUCCESS('Successfully generated combined PDF report'))