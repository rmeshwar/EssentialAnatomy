from django.core.management.base import BaseCommand
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import PageBreak, Paragraph
from django.conf import settings
from django.db.models import Count
import os
from django.contrib.staticfiles.storage import staticfiles_storage
import json
from myapp.models import (
    Section, Subsection, Element, Topic, ResponseTopic,
    ProcessedResponseAnatomy, ProcessedResponseClinician, ResponderAnatomy, ResponderClinician
)

class Command(BaseCommand):
    help = 'Generate a PDF report of survey results'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data',
            type=str,
            help='JSON string of form data (profession, disciplines, regions)',
            required=True
        )

    def handle(self, *args, **kwargs):
        form_data_json = kwargs['data']
        # print("DEBUG: Raw input JSON to generate_report.py:")
        # print(form_data_json)
        try:
            form_data = json.loads(form_data_json)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Invalid JSON: {e}"))
            return
        
        profession = form_data.get('profession', '')
        columns_array = form_data.get('columns', [])
        selected_regions = form_data.get('regions', [])

        if not profession:
            self.stdout.write(self.style.ERROR("No profession selected; cannot generate report."))
            return

        # Load parsed_structure.json to handle main groups and subgroups
        try:
            json_file_path = staticfiles_storage.path('data/parsed_structure.json')
            with open(json_file_path, 'r') as f:
                parsed_structure = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(
                f'File not found: {json_file_path}. Please ensure the file exists and is in the correct location.'))
            return

        # Expand the parsed structure into a flattened dictionary
        expanded_categories, abbreviations_map = self.expand_structure(parsed_structure)

        processed_responses = []

        for col in columns_array:
            parent = col.get("parent")
            child = col.get("child")  # might be None
            deselected_children = col.get("deselected", None)

            # Build a full_key string like "Anatomist" or "Anatomist / Dentistry"
            if child:
                full_key = f"{parent} / {child}"
            else:
                full_key = parent

            print(f"Processing {full_key} - Deselected: {deselected_children}")
            self.add_processed_response(full_key, processed_responses, expanded_categories, deselected_children)

        # no more direct calls

        print("DEBUG: Final processed_responses:")
        for pr in processed_responses:
            print(pr)



        # If no processed_responses, we cannot generate a real PDF
        if not processed_responses:
            self.stdout.write(self.style.ERROR("No valid categories found to generate a report."))
            return

        self.selected_regions = selected_regions  # Not used by default, but could be integrated in the future

        # The rest is the original PDF generation logic
        self.generate_pdf_report(processed_responses, expanded_categories, abbreviations_map, columns_array)

    
    def add_processed_response(self, full_key, processed_list, expanded, deselected_children=None):
        matched_category = expanded.get(full_key)
        if not matched_category:
            return

        category_parts = full_key.split(" / ")
        parent = category_parts[0]

        # If this is a parent-level entry with no child, and children were deselected:
        if len(category_parts) == 1 and deselected_children is not None:
            # Get all known children from the expanded structure
            all_children = {
                key.split(" / ")[1]
                for key in expanded
                if key.startswith(f"{parent} /") and len(key.split(" / ")) == 2
            }

            # If all children were excluded, skip adding this response
            if set(deselected_children) >= all_children:
                # print(f"EXCLUDING {full_key} entirely because all children were deselected")
                return

        if category_parts[0] == "Anatomist":
            if deselected_children:
                print(f"Checking exclusions for {full_key} - Deselected: {deselected_children}")  # Debugging
                if len(category_parts) > 1:  # Check if this is a child category
                    child_name = category_parts[1]
                    if child_name in deselected_children:
                        # print(f"EXCLUDING {full_key} from report due to deselection.")  # DEBUG
                        return  # Skip adding this to the processed responses
                else:
                    print(f"KEEPING {full_key}, not in deselected list.")  # Debugging

            print(f"ADDING {full_key} to processed_responses")  # DEBUG
            processed_list.append({
                "model": ProcessedResponseAnatomy,
                "label": matched_category['label'],
                "full_key": full_key,
                "is_anatomist": True,
                "query": {},
                "exclusions": set(deselected_children) if deselected_children else set()
            })
        elif category_parts[0] == "Clinician":
            professional_health_program = category_parts[1] if len(category_parts) > 1 else None

            if len(category_parts) == 1 and deselected_children is not None:
                # Check if all children are excluded
                all_children = {
                    key.split(" / ")[1]
                    for key in expanded
                    if key.startswith("Clinician /") and len(key.split(" / ")) == 2
                }
                if set(deselected_children) >= all_children:
                    print(f"EXCLUDING {full_key} entirely because all children were deselected")  # DEBUG
                    return

            if deselected_children:
                if len(category_parts) > 1:
                    child_name = category_parts[1]
                    if child_name in deselected_children:
                        return
                else:
                    print(f"KEEPING {full_key}, not in deselected list.")  # Debugging

            print(f"ADDING {full_key} to processed_responses")  # DEBUG
            processed_list.append({
                "model": ProcessedResponseClinician,
                "label": matched_category['label'],
                "full_key": full_key,
                "is_anatomist": False,
                # NEW:
                "query": {
                    **({"professional_health_program": professional_health_program} if professional_health_program else {}),
                    "primary_field": None,
                    "subfield": None
                },

                "exclusions": set(deselected_children) if deselected_children else set()
            })

            # if len(category_parts) == 2:
            #     professional_health_program = category_parts[1]

            #     # Check if an entry with this full_key already exists
            #     if not any(entry["full_key"] == full_key for entry in processed_list):
            #         processed_list.append({
            #             "model": ProcessedResponseClinician,
            #             "label": matched_category['label'],
            #             "full_key": full_key,
            #             "is_anatomist": False,
            #             "query": {
            #                 "professional_health_program": professional_health_program,
            #                 "primary_field": None,  # Placeholder for later filtering
            #                 "subfield": None  # Placeholder for later filtering
            #             },
            #             "exclusions": set(deselected_children) if deselected_children else set()
            #         })




    def expand_structure(self, structure, parent_key='', parent_abbr=''):
        expanded = {}
        abbreviations_map = {}  # Dictionary to map abbreviations to full labels

        for key, value in structure.items():
            current_key = f"{parent_key} / {key}".strip() if parent_key else key
            if parent_abbr:
                current_abbr = f"{parent_abbr}/{value.get('abbr', key)}"
            else:
                current_abbr = value.get('abbr', key)

            expanded[current_key] = {"label": key, "abbr": current_abbr, "parent": parent_key}
            abbreviations_map[current_abbr] = current_key  # Map abbreviation to the full label

            if 'subgroups' in value:
                sub_expanded, sub_abbreviations = self.expand_structure(value['subgroups'], current_key, current_abbr)
                expanded.update(sub_expanded)
                abbreviations_map.update(sub_abbreviations)

            if 'specialties' in value:
                for specialty in value['specialties']:
                    specialty_key = f"{current_key} / {specialty['name']}".strip()
                    specialty_abbr = f"{current_abbr}/{specialty.get('abbr', specialty['name'])}"
                    expanded[specialty_key] = {"label": specialty['name'], "abbr": specialty_abbr, "parent": current_key}
                    abbreviations_map[specialty_abbr] = specialty_key

        return expanded, abbreviations_map

    def generate_pdf_report(self, processed_responses, expanded_categories, abbreviations_map, columns_array):
        def get_color_for_rating(rating):
            """Return a specific color for each rating range using the provided hex values."""
            if 1 <= rating <= 2.5:
                return colors.HexColor("#F4B083")  # Red (Not Important)
            elif 2.5 < rating <= 4:
                return colors.HexColor("#FFE49A")  # Yellow (Less Important)
            elif 4 < rating <= 5.5:
                return colors.HexColor("#BDD6EE")  # Blue (More Important)
            elif 5.5 < rating <= 7:
                return colors.HexColor("#92D051")  # Green (Essential)
            else:
                return colors.white  # Default to white if rating is unexpected



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

        # Build the report table data
        if self.selected_regions:
            sections = Section.objects.filter(name__in=self.selected_regions)
        else:
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
                            category_parts = response["full_key"].split(" / ")
                            if len(category_parts) > 1:  # This is a child category
                                child_name = category_parts[1]
                                if child_name in response.get("exclusions", set()):
                                    # print(f"Skipping {response['full_key']} in PDF generation due to deselection")  # Debugging
                                    continue  # Skip this child
                            processed_model, query = response['model'], response['query']
                            exclusions = response.get('exclusions', set())

                            exclusions = response.get("exclusions", set())  # Retrieve stored exclusions
                            # print(f"Filtering responders for {response['full_key']} - Excluding: {exclusions}")  # Debugging
                            responders = self.get_responders(response, exclusions, expanded_categories)


                            # For ResponderAnatomy and ProcessedResponseAnatomy
                            if response['is_anatomist']:
                                responder_programs = responders.values_list('professional_health_program', flat=True)
                                processed_response_qs = processed_model.objects.filter(
                                    subsubgroup_id=response_topic.id,
                                    professional_health_program__in=responder_programs
                                )
                                # print(f"\n--- DEBUG: Processing {response['full_key']} ---")
                                # print(f"Responder programs: {list(responder_programs)}")
                                # print(f"Subsubgroup ID: {response_topic.id}")
                                # print(f"Queryset count: {processed_response_qs.count()}")
                                # print(f"Excluded children: {response.get('exclusions')}")
                            else:
                                # For ResponderClinician and ProcessedResponseClinician
                                responder_programs = responders.values_list('professional_health_program', flat=True)
                                processed_response_qs = processed_model.objects.filter(
                                    subsubgroup_id=response_topic.id,
                                    professional_health_program__in=responder_programs
                                )
                                # print(f"\n--- DEBUG: Processing {response['full_key']} ---")
                                # print(f"Responder programs: {list(responder_programs)}")
                                # print(f"Subsubgroup ID: {response_topic.id}")
                                # print(f"Queryset count: {processed_response_qs.count()}")
                                # print(f"Excluded children: {response.get('exclusions')}")
                                # print(f"Final QuerySet (Clinician): {processed_response_qs.query}")

                                # If primary_field exists, further refine the query
                                if response.get('query', {}).get('primary_field'):
                                    processed_response_qs = processed_response_qs.filter(
                                        primary_field=response['query']['primary_field']
                                    )

                                # If subfield exists, further refine the query
                                if response.get('query', {}).get('subfield'):
                                    processed_response_qs = processed_response_qs.filter(
                                        subfield=response['query']['subfield']
                                    )


                            if processed_response_qs.exists():
                                abbr = expanded_categories[response['full_key']]['abbr']
                                abbreviations_used.add(abbr)

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
                    else:
                        row = [Paragraph(f"{topic.name}", blue_text_style)]
                        # Add abbreviation and count of responses (n={x})
                        small_red_text_style = ParagraphStyle(name='SmallRedText', parent=styles['Normal'],
                                                              textColor=colors.red, fontSize=8)

                        for response in processed_responses:
                            abbr = expanded_categories[response['full_key']]['abbr']
                            abbreviations_used.add(abbr)

                            # Calculate the count (number of responses for this category)
                            exclusions = response.get("exclusions", set())  # Retrieve stored exclusions
                            # print(f"Filtering responders for {response['full_key']} - Excluding: {exclusions}")  # Debugging
                            responders = self.get_responders(response, exclusions, expanded_categories)


                            # Format abbreviation with count "n={x}"
                            count = responders.count()
                            abbr_with_count = f"{abbr} <font color='red' size='8'>n={count}</font>"
                            row.append(Paragraph(abbr_with_count, styles['Heading3']))
                            abbreviations_used.add(abbr)
                        row.append(Paragraph("Total", styles['Heading3']))
                        section_data.append(row)

                    elements_query = Element.objects.filter(topic=topic)
                    for element in elements_query:
                        response_topic = ResponseTopic.objects.filter(element=element).first()
                        if response_topic:
                            row = [Paragraph(f"{element.name}", styles['Normal'])]
                            total_ratings = []
                            for response in processed_responses:
                                category_parts = response["full_key"].split(" / ")
                                if len(category_parts) > 1:  # This is a child category
                                    child_name = category_parts[1]
                                    if child_name in response.get("exclusions", set()):
                                        # print(f"Skipping {response['full_key']} in PDF generation due to deselection")  # Debugging
                                        continue  # Skip this child

                                processed_model, query = response['model'], response['query']
                                exclusions = response.get('exclusions', set())

                                exclusions = response.get("exclusions", set())  # Retrieve stored exclusions
                                # print(f"Filtering responders for {response['full_key']} - Excluding: {exclusions}")  # Debugging
                                responders = self.get_responders(response, exclusions, expanded_categories)


                                if response['is_anatomist']:
                                    responder_programs = responders.values_list('professional_health_program',
                                                                                flat=True)
                                    processed_response_qs = processed_model.objects.filter(
                                        subsubgroup_id=response_topic.id,
                                        professional_health_program__in=responder_programs
                                    )
                                    # print(f"\n--- DEBUG: Processing {response['full_key']} ---")
                                    # print(f"Responder programs: {list(responder_programs)}")
                                    # print(f"Subsubgroup ID: {response_topic.id}")
                                    # print(f"Queryset count: {processed_response_qs.count()}")
                                    # print(f"Excluded children: {response.get('exclusions')}")

                                else:
                                    responder_programs = responders.values_list('professional_health_program',
                                                                                flat=True)
                                    processed_response_qs = processed_model.objects.filter(
                                        subsubgroup_id=response_topic.id,
                                        professional_health_program__in=responder_programs
                                    )
                                    # print(f"\n--- DEBUG: Processing {response['full_key']} ---")
                                    # print(f"Responder programs: {list(responder_programs)}")
                                    # print(f"Subsubgroup ID: {response_topic.id}")
                                    # print(f"Queryset count: {processed_response_qs.count()}")
                                    # print(f"Excluded children: {response.get('exclusions')}")
                                    # print(f"Final QuerySet (Clinician): {processed_response_qs.query}")

                                    # If primary_field exists, further refine the query
                                    if response.get('query', {}).get('primary_field'):
                                        processed_response_qs = processed_response_qs.filter(
                                            primary_field=response['query']['primary_field']
                                        )

                                    # If subfield exists, further refine the query
                                    if response.get('query', {}).get('subfield'):
                                        processed_response_qs = processed_response_qs.filter(
                                            subfield=response['query']['subfield']
                                        )


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

            unique_headers = []
            seen_headers = set()

            for response in processed_responses:
                if response["full_key"] not in seen_headers:
                    unique_headers.append(Paragraph(response['label'], styles['Heading3']))
                    seen_headers.add(response["full_key"])

            header = [Paragraph('', styles['Heading3'])] + unique_headers + [Paragraph("Total", styles['Heading3'])]

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
                max_width = (letter[0] - reserved_space_on_right - 20 * mm)  # Total page width minus reserved space and left margin
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
                    
        included_summary_data = [["Parent", "Included Children"]]
        excluded_summary_data = [["Parent", "Excluded Children"]]
        
        # We'll map e.g. "Anatomist" -> set(["Dentistry", "Nursing"]) 
        # but also handle the case where we had "child=None"
        parent_map = {}
        for pr in processed_responses:
            full_key = pr["full_key"]
            parts = full_key.split(" / ")
            if len(parts) == 1:
                # Only parent
                the_parent = parts[0]
                if the_parent not in parent_map:
                    parent_map[the_parent] = set()
            elif len(parts) == 2:
                the_parent, child = parts
                if the_parent not in parent_map:
                    parent_map[the_parent] = set()
                parent_map[the_parent].add(child)
        
        wrapped_style = ParagraphStyle(name="WrappedText", fontSize=10, leading=12, alignment=TA_LEFT, wordWrap="CJK")

        # Step 1: Get children with data in Processed tables
        anatomist_children = set(
            ProcessedResponseAnatomy.objects
            .values_list('professional_health_program', flat=True)
            .annotate(count=Count('id'))
            .filter(count__gt=0)
        )

        clinician_children = set(
            ProcessedResponseClinician.objects
            .values_list('professional_health_program', flat=True)
            .annotate(count=Count('id'))
            .filter(count__gt=0)
        )

        # Build a map of all children per parent from the parsed structure
        all_possible_children = {}
        for col in columns_array:
            parent = col.get("parent")
            # Get all children under this parent from the parsed structure
            if parent == "Anatomist":
                children = [
                    key.split(" / ")[-1]
                    for key in expanded_categories
                    if key.startswith("Anatomist /") and len(key.split(" / ")) == 2 and key.split(" / ")[-1] in anatomist_children
                ]
            elif parent == "Clinician":
                children = [
                    key.split(" / ")[-1]
                    for key in expanded_categories
                    if key.startswith("Clinician /") and len(key.split(" / ")) == 2 and key.split(" / ")[-1] in clinician_children
                ]
            else:
                children = []  # fallback
            all_possible_children[parent] = set(children)

        for parent in all_possible_children:
            excluded_children = set(
                next(
                    (col["deselected"] for col in columns_array
                    if col.get("parent") == parent and col.get("deselected") is not None),
                    []
                )
            )
            included_children = all_possible_children[parent] - excluded_children

            print(f"[SUMMARY] {parent} included: {included_children}")
            print(f"[SUMMARY] {parent} excluded: {excluded_children}")

            if included_children:
                included_text = Paragraph(", ".join(sorted(included_children)), wrapped_style)
                included_summary_data.append([parent, included_text])
            else:
                included_summary_data.append([parent, Paragraph("None (all children excluded)", wrapped_style)])

            if excluded_children:
                excluded_text = Paragraph(", ".join(sorted(excluded_children)), wrapped_style)
                excluded_summary_data.append([parent, excluded_text])

                    
        centered_style = ParagraphStyle(name="CenteredText", parent=getSampleStyleSheet()["Heading2"], alignment=TA_CENTER)

        # Included Table
        elements.append(PageBreak())
        elements.append(Paragraph("Included Disciplines", centered_style))
        included_table = Table(included_summary_data, colWidths=[3 * inch, 4 * inch])
        included_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(included_table)

        # Excluded Table
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Excluded Disciplines", centered_style))
        excluded_table = Table(excluded_summary_data, colWidths=[3 * inch, 4 * inch])
        excluded_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(excluded_table)        

        # Add a Color Key Section at the End
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Color Key", centered_style))

        # Define colors and labels
        color_labels = [
            ("#F4B083", "Not Important (1-2.5)"),
            ("#FFE49A", "Less Important (2.5-4)"),
            ("#BDD6EE", "More Important (4-5.5)"),
            ("#92D051", "Essential (5.5-7)")
        ]

        # Create table data for color key
        color_key_data = [[Paragraph(label, getSampleStyleSheet()['Normal']), " "] for _, label in color_labels]

        # Style and add color backgrounds
        color_key_table = Table(color_key_data, colWidths=[2.5 * inch, 0.5 * inch])
        color_key_table.setStyle(TableStyle([
            ('BACKGROUND', (1, i), (1, i), colors.HexColor(color)) for i, (color, _) in enumerate(color_labels)
        ] + [
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT')
        ]))

        # Ensure alignment with left margin
        elements.append(color_key_table)

        

        # Generate PDF with updated function call
        doc.build(elements,
                  onFirstPage=lambda canvas, doc: add_page_number(canvas, doc, abbreviations_used, abbreviations_map),
                  onLaterPages=lambda canvas, doc: add_page_number(canvas, doc, abbreviations_used, abbreviations_map))

        self.stdout.write(self.style.SUCCESS('Successfully generated combined PDF report'))

    def get_responders(self, response, exclusions, expanded_categories):
        # Fetch responders for the given response, excluding those from deselected subcategories
        if response['is_anatomist']:
            responders = ResponderAnatomy.objects.all()
            if response['full_key'] != "Anatomist":
                responders = responders.filter(
                    professional_health_program=response['label']
                )
            # Exclude responders from deselected subcategories
            if exclusions:
                excluded_programs = set()
                for ex in exclusions:
                    if ex in expanded_categories:
                        excluded_programs.add(expanded_categories[ex]['label'])
                    else:
                        excluded_programs.add(ex)  # Fallback in case it’s already a string

                print(f"Filtering responders for {response['full_key']} - Excluding: {excluded_programs}")  # DEBUG
                responders = responders.exclude(professional_health_program__in=excluded_programs)
        else:
            responders = ResponderClinician.objects.all()
            if 'professional_health_program' in response['query']:
                responders = responders.filter(
                    professional_health_program=response['query']['professional_health_program']
                )

            if 'primary_field' in response['query'] and response['query']['primary_field']:
                responders = responders.filter(primary_field=response['query']['primary_field'])

            if 'subfield' in response['query'] and response['query']['subfield']:
                responders = responders.filter(subfield=response['query']['subfield'])

            # Exclude responders from deselected subcategories
            if exclusions:
                excluded_programs = set()
                for ex in exclusions:
                    # If exclusion is a full key, get its label
                    if ex in expanded_categories:
                        excluded_programs.add(expanded_categories[ex]['label'])
                    else:
                        excluded_programs.add(ex)  # fallback
                print(f"Filtering responders for {response['full_key']} - Excluding: {excluded_programs}")
                responders = responders.exclude(professional_health_program__in=excluded_programs)


        # # print(f"Responders for {response['full_key']} (after exclusions):")
        # for r in responders:
        #     print(f" - {r.professional_health_program} | {getattr(r, 'primary_field', '')} | {getattr(r, 'subfield', '')}")

        return responders