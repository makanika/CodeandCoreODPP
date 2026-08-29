from django.db import models


class Region(models.Model):
	code = models.CharField(max_length=24, unique=True)
	name = models.CharField(max_length=120, unique=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name


class Office(models.Model):
	class OfficeType(models.TextChoices):
		HEADQUARTERS = 'HEADQUARTERS', 'Headquarters'
		REGIONAL_DPP = 'REGIONAL_DPP', 'Regional DPP Office'
		POLICE_STATION = 'POLICE_STATION', 'Police Station'
		REGISTRY = 'REGISTRY', 'Registry'
		DIRECTORATE = 'DIRECTORATE', 'Directorate'
		DEPARTMENT = 'DEPARTMENT', 'Department'

	code = models.CharField(max_length=24, unique=True)
	name = models.CharField(max_length=160, unique=True)
	office_type = models.CharField(max_length=24, choices=OfficeType.choices)
	region = models.ForeignKey(Region, null=True, blank=True, on_delete=models.PROTECT, related_name='offices')
	parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='child_offices')
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name
