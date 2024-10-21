from django.db import models

class Section(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Subsection(models.Model):
    section = models.ForeignKey(Section, related_name='subsections', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Topic(models.Model):
    subsection = models.ForeignKey(Subsection, related_name='topics', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

class Element(models.Model):
    topic = models.ForeignKey(Topic, related_name='elements', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

class ResponseTopic(models.Model):
    name = models.CharField(max_length=200)
    is_element = models.BooleanField(default=False)
    topic = models.ForeignKey(Topic, null=True, blank=True, on_delete=models.CASCADE)
    element = models.ForeignKey(Element, null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class ResponderAnatomy(models.Model):
    responder_id = models.IntegerField(default=0)
    terminal_degree = models.CharField(max_length=255)
    professional_health_program = models.CharField(max_length=255)
    program_category = models.CharField(max_length=10, default='MISC')

    def __str__(self):
        return f"{self.terminal_degree} - {self.professional_health_program}"

class SubgroupResponseAnatomy(models.Model):
    responder = models.ForeignKey(ResponderAnatomy, related_name='subgroup_responses_anatomy', on_delete=models.CASCADE)
    subgroup = models.ForeignKey(Subsection, related_name='responses_anatomy', on_delete=models.CASCADE)
    rating = models.IntegerField()

    def __str__(self):
        return f"{self.responder} - {self.subgroup.name}: {self.rating}"

class SubSubgroupResponseAnatomy(models.Model):
    responder = models.ForeignKey(ResponderAnatomy, related_name='subsubgroup_responses_anatomy', on_delete=models.CASCADE)
    subsubgroup = models.ForeignKey(ResponseTopic, related_name='responses_anatomy', on_delete=models.CASCADE)
    rating = models.IntegerField()

    def __str__(self):
        return f"{self.responder} - {self.subsubgroup.name}: {self.rating}"

class ProcessedResponseAnatomy(models.Model):
    subsubgroup = models.ForeignKey(ResponseTopic, on_delete=models.CASCADE, related_name='processed_responses_anatomy')
    average_rating = models.FloatField(null=True, blank=True)
    professional_health_program = models.CharField(max_length=255, null=True, blank=True)
    rating_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.subsubgroup} - {self.professional_health_program} - {self.average_rating}"


from django.db import models


class ResponderClinician(models.Model):
    responder_id = models.IntegerField(default=0)
    terminal_degree = models.CharField(max_length=255)
    professional_health_program = models.CharField(max_length=255)
    program_category = models.CharField(max_length=10, default='MISC')

    primary_field = models.CharField(max_length=255, null=True, blank=True)
    subfield = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.terminal_degree} - {self.professional_health_program} - {self.primary_field} - {self.subfield}"


class SubgroupResponseClinician(models.Model):
    responder = models.ForeignKey(ResponderClinician, related_name='subgroup_responses_clinician', on_delete=models.CASCADE)
    subgroup = models.ForeignKey(Subsection, related_name='responses_clinician', on_delete=models.CASCADE)
    rating = models.IntegerField()

    def __str__(self):
        return f"{self.responder} - {self.subgroup.name}: {self.rating}"

class SubSubgroupResponseClinician(models.Model):
    responder = models.ForeignKey(ResponderClinician, related_name='subsubgroup_responses_clinician', on_delete=models.CASCADE)
    subsubgroup = models.ForeignKey(ResponseTopic, related_name='responses_clinician', on_delete=models.CASCADE)
    rating = models.IntegerField()

    def __str__(self):
        return f"{self.responder} - {self.subsubgroup.name}: {self.rating}"

class ProcessedResponseClinician(models.Model):
    subsubgroup = models.ForeignKey(ResponseTopic, on_delete=models.CASCADE, related_name='processed_responses_clinician')
    average_rating = models.FloatField(null=True, blank=True)
    professional_health_program = models.CharField(max_length=255, null=True, blank=True)
    primary_field = models.CharField(max_length=255, null=True, blank=True)
    subfield = models.CharField(max_length=255, null=True, blank=True)
    rating_count = models.IntegerField(null=True, blank=True)  # New field to store count of ratings

    def __str__(self):
        return f"{self.subsubgroup} - {self.professional_health_program} - {self.average_rating} - Count: {self.rating_count}"
