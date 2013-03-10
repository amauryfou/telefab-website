# This file uses the following encoding: utf-8

from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils.timezone import get_default_timezone as tz
from telefab.local_settings import WEBSITE_CONFIG
from telefab.settings import ANIMATORS_GROUP_NAME, MAIN_PLACE_NAME
from django.core.urlresolvers import reverse
from datetime import datetime

class UserProfile(models.Model):
	"""
	Represents extra data on an user
	"""
	class Meta:
		verbose_name = u"profil"
		verbose_name_plural = u"profils"
	
	user = models.ForeignKey(User, verbose_name = u"utilisateur", unique = True)
	description = models.TextField(verbose_name = u"description", blank = True)
	
	def __unicode__(self):
		"""
		Returns a string representation
		"""
		if self.user.first_name:
			return self.user.first_name + u" " + self.user.last_name
		else:
			name = self.user.email.rsplit('@')[0].split('.')
			cap_name = []
			for word in name:
				cap_name.append(word.capitalize())
			return ' '.join(cap_name)

	def is_animator(self):
		"""
		Has this user animator rights?
		"""
		return len(self.user.groups.filter(name = ANIMATORS_GROUP_NAME)) > 0

	def is_blog_user(self):
		"""
		Is this django user also a blog user?
		"""
		return len(BlogUser.objects.filter(user_email=self.user.email)) > 0

	@staticmethod
	def get_animators():
		"""
		Return the list of all animators
		"""
		return User.objects.filter(groups__name = ANIMATORS_GROUP_NAME)

class Event(models.Model):
	"""
	Represents an event in the FabLab: opening, session...
	"""
	class Meta:
		verbose_name = u"évènement"
		verbose_name_plural = u"évènements"
	
	start_time = models.DateTimeField(verbose_name = u"début")
	end_time = models.DateTimeField(verbose_name = u"fin")
	EVENT_CATEGORIES = (
		(0, u"Ouverture"),
		(1, u"Atelier"),
		(2, u"Discussion")
	)
	EVENT_CATEGORY_IDS = ['open', 'session', 'talk']
	category = models.IntegerField(verbose_name = u"type", choices = EVENT_CATEGORIES, default = 0)
	location = models.CharField(verbose_name=u"lieu", max_length = 25, default = u"Téléfab Brest")
	title = models.CharField(verbose_name = u"titre", max_length = 50, blank = True)
	description = models.TextField(verbose_name = u"description", blank = True)
	link = models.CharField(verbose_name=u"lien", max_length = 200, blank=True)
	animators = models.ManyToManyField(User, verbose_name = u"animateurs", blank = True, limit_choices_to = Q(groups__name = ANIMATORS_GROUP_NAME))
	
	def category_id(self):
		"""
		Returns the identifier of the category of this event
		"""
		if self.category is None:
			return None
		return self.EVENT_CATEGORY_IDS[self.category]
	
	def category_name(self):
		"""
		Returns the name of the category of this event
		"""
		for id, name in dict(self.EVENT_CATEGORIES).iteritems():
			if id == self.category:
				return name
		return None
	
	def global_title(self):
		"""
		String representing the title depending on the type
		"""
		if self.category == 0:
			if len(self.animators.all()) > 0:
				result = u"Ouvert"
			else:
				result = u"Libre-service"
		else:
			result = self.title
		return result
	
	def animators_list(self):
		"""
		String describing the animators
		"""
		anims = self.animators.all()
		if len(anims) == 0:
			return None
		else:
			desc = u""
			first = True
			for animator in anims:
				if first:
					sep = u""
					first = False
				else:
					sep = u", "
				desc = desc + sep + unicode(animator.get_profile())
			return desc

	def absolute_link(self):
		"""
		The absolute information link (if easy to find)
		"""
		if self.link[0] == '/':
			return WEBSITE_CONFIG["protocol"] + '://' + WEBSITE_CONFIG["host"] + WEBSITE_CONFIG["path"] + self.link
		else:
			return self.link
	
	def __unicode__(self):
		"""
		Returns a string representation
		"""
		return self.category_name() + u" du " + self.start_time.astimezone(tz()).strftime(u"%d/%m/%Y %H:%M") + u" au " + self.end_time.astimezone(tz()).strftime(u"%d/%m/%Y %H:%M")
    
	def get_absolute_url(self):
		"""
		Return the public URL to this object
		"""
		return reverse("main.views.show_events", kwargs={'day': self.start_time.astimezone(tz()).strftime(u"%d"), 'month': self.start_time.astimezone(tz()).strftime(u"%m"), 'year': self.start_time.astimezone(tz()).strftime(u"%Y")})

class Equipment(models.Model):
	"""
	Represents equipment available in the FabLab
	"""
	class Meta:
		verbose_name = u"équipement"
		verbose_name_plural = u"matériel"

	manufacturer = models.ForeignKey("EquipmentManufacturer", verbose_name = u"fabriquant", blank = True, null = True)
	category = models.ForeignKey("EquipmentCategory", verbose_name = u"type")
	name = models.CharField(verbose_name = u"nom", max_length = 100)
	reference = models.CharField(verbose_name = u"référence", max_length = 100, blank = True)
	description = models.TextField(verbose_name = u"description", blank = True)
	quantity = models.PositiveIntegerField(verbose_name = u"quantité", default = 1)
	location = models.CharField(verbose_name = u"emplacement", max_length = 100, blank = True)
	link = models.URLField(verbose_name = u"lien", blank = True)
	datasheet = models.FileField(verbose_name = u"datasheet", upload_to = "datasheet", blank = True, null = True)
	
	def __unicode__(self):
		"""
		Returns a string representation
		"""
		return self.name
    
	def get_absolute_url(self):
		"""
		Return the public URL to this object
		"""
		return reverse("main.views.show_equipment_categories")

	def available_quantity(self):
		"""
		Return the quantity not currently away in a loan
		"""
		available_quantity = self.quantity
		for equipment_loan in EquipmentLoan.objects.filter(equipment = self):
			if equipment_loan.loan.is_away():
				available_quantity-= equipment_loan.quantity
		return available_quantity


class EquipmentManufacturer(models.Model):
	"""
	Represents a manufacturer
	"""
	class Meta:
		verbose_name = u"fabriquant"
		verbose_name_plural = u"fabriquants"

	name = models.CharField(verbose_name = u"nom", max_length = 100)

	def __unicode__(self):
		"""
		Returns a string representation
		"""
		return self.name

class EquipmentCategory(models.Model):
	"""
	Represents an equipment type
	"""
	class Meta:
		verbose_name = u"type de matériel"
		verbose_name_plural = u"types de matériel"

	name = models.CharField(verbose_name = u"nom", max_length = 100)
	slug = models.SlugField(verbose_name = u"permalien", max_length = 100)

	def __unicode__(self):
		"""
		Returns a string representation
		"""
		return self.name



class Loan(models.Model):
	"""
	Represents a loan of some equipment
	"""
	class Meta:
		verbose_name = u"prêt"
		verbose_name_plural = u"prêts"

	borrower = models.ForeignKey(User, verbose_name = u"emprunteur", blank = True, null=True, related_name='loans')
	borrower_name = models.CharField(verbose_name = u"nom de l'emprunteur", max_length = 100, blank = True, null=True)
	equipments = models.ManyToManyField(Equipment, verbose_name=u"matériel", through="EquipmentLoan")
	comment = models.TextField(verbose_name = u"commentaire", blank = True)
	request_time = models.DateTimeField(verbose_name = u"date de la demande", blank = True, null=True)
	loan_time = models.DateTimeField(verbose_name = u"date du prêt", blank = True, null=True)
	lender = models.ForeignKey(User, verbose_name = u"prêteur", blank = True, null=True, related_name='validated_loans', limit_choices_to = Q(groups__name = ANIMATORS_GROUP_NAME))
	scheduled_return_date = models.DateField(verbose_name = u"date de retour programmée", blank = True, null=True)
	return_time = models.DateTimeField(verbose_name = u"date de retour", blank = True, null=True)
	cancel_time = models.DateTimeField(verbose_name = u"date d'annulation", blank = True, null=True)
	cancelled_by = models.ForeignKey(User, verbose_name = u"annulé par", blank = True, null=True, related_name='cancelled_loans')

	def __unicode__(self):
		"""
		String representation of the loan
		"""
		return u"Emprunt par " + self.borrower_display()

	def borrower_display(self):
		"""
		Name of the borrower to display
		"""
		if self.borrower:
			return unicode(self.borrower.get_profile())
		else:
			return self.borrower_name
	borrower_display.short_description = u"emprunteur"

	def is_waiting(self):
		"""
		Is the loan requested and not given?
		"""
		return self.request_time is not None and self.loan_time is None and self.cancel_time is None
	is_waiting.boolean = True
	is_waiting.short_description = u"en attente"

	def is_away(self):
		"""
		Is the equipment away?
		"""
		return self.loan_time is not None and self.return_time is None and self.cancel_time is None
	is_away.boolean = True
	is_away.short_description = u"prêt en cours"

	def is_returned(self):
		"""
		Has the loan been returned?
		"""
		return self.return_time is not None
	is_returned.boolean = True
	is_returned.short_description = u"rendu"

	def is_cancelled(self):
		"""
		Has the loan been cancelled?
		"""
		return self.cancel_time is not None
	is_cancelled.boolean = True
	is_cancelled.short_description = u"annulé"


class EquipmentLoan(models.Model):
	"""
	Binds an equipment to a loan. Includes the number of pieces loaned
	"""
	class Meta:
		verbose_name = "équipement"
		verbose_name_plural = "matériel"
	equipment = models.ForeignKey(Equipment, verbose_name = u"équipement")
	loan = models.ForeignKey(Loan, related_name="bookings")
	quantity = models.PositiveIntegerField(verbose_name = u"quantité", default = 1)

	def __unicode__(self):
		"""
		String representation of the equipment loan
		"""
		return unicode(self.equipment)

class Place(models.Model):
	"""
	Place with a monitored opening state
	"""
	class Meta:
		verbose_name = "lieu"
		verbose_name_plural = "lieux"
	name = models.CharField(verbose_name = u"nom", max_length = 100)

	def current_opening(self):
		"""
		Return the current opening if any, or None
		"""
		now = datetime.now(tz())
		try:
			return self.openings.get(Q(start_time__lte=now, end_time__gt=now) | Q(start_time__lte=now, end_time=None))
		except PlaceOpening.DoesNotExist:
			return None

	def now_open(self):
		"""
		Is this place currently open?
		"""
		return self.current_opening() is not None

	def do_open_now(self, animator = None):
		"""
		Set the place as currently open, return the opening if it was sucessful or null
		"""
		if self.now_open():
			return None
		return self.openings.create(start_time = datetime.now(), animator = animator)

	def do_close_now(self, animator = None):
		"""
		Set the place as currently closed, return the opening if it was sucessful or null
		"""
		opening = self.current_opening()
		if opening is None:
			return None
		opening.end_time = datetime.now()
		opening.save()
		return opening

	def __unicode__(self):
		"""
		String representation
		"""
		return self.name

	@staticmethod
	def get_main_place():
		"""
		Return the main place
		"""
		return Place.objects.get(name = MAIN_PLACE_NAME)

class PlaceOpening(models.Model):
	"""
	Opening period of a place
	"""
	class Meta:
		verbose_name = "ouverture"
		verbose_name_plural = "ouvertures"

	place = models.ForeignKey(Place, verbose_name = u"lieu", related_name='openings')
	start_time = models.DateTimeField(verbose_name = u"début")
	end_time = models.DateTimeField(verbose_name = u"fin", blank = True, null = True)
	animator = models.ForeignKey(User, verbose_name = u"animateur", blank=True, null = True, limit_choices_to = Q(groups__name = ANIMATORS_GROUP_NAME))
	
	def __unicode__(self):
		"""
		Returns a string representation
		"""
		if self.end_time is not None:
			return self.place.name + u" du " + self.start_time.astimezone(tz()).strftime(u"%d/%m/%Y %H:%M") + u" au " + self.end_time.astimezone(tz()).strftime(u"%d/%m/%Y %H:%M")
		else:
			return self.place.name + u" du " + self.start_time.astimezone(tz()).strftime(u"%d/%m/%Y %H:%M") + u" à maintenant"

class BlogUser(models.Model):
	"""
	Link to the WordPress user table to add/check users
	"""
	class Meta:
		db_table = "wp_users"
		managed = False

	ID = models.AutoField(primary_key=True)
	user_login = models.CharField(max_length=60)
	user_nicename = models.CharField(max_length=50)
	user_email = models.EmailField(max_length=100)
	user_registered = models.DateTimeField(auto_now=True)
	display_name = models.CharField(max_length=250)
		