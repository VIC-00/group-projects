from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('landlord', 'Landlord'),
        ('tenant', 'Tenant'),
        ('maintenance', 'Maintenance Staff'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='tenant')
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

class Property(models.Model):
    # This links the property to a specific landlord
    landlord = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'landlord'},
        related_name='owned_properties',
        null=True,   # Temporarily allow null so your existing data doesn't break
        blank=True
    )
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    total_units = models.IntegerField(default=1)
    monthly_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

    @property
    def vacant_units(self):
        # Occupancy is now calculated relative to this property only
        occupied = Tenant.objects.filter(assigned_property=self).count()
        return self.total_units - occupied
class Tenant(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    assigned_property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True)
    unit_number = models.CharField(max_length=10, blank=True) # e.g., "B4"
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    lease_end = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Payment(models.Model):
    STATUS_CHOICES = (('confirmed', 'Confirmed'), ('pending', 'Pending'), ('failed', 'Failed'))
    
    # Define the method options here
    METHOD_CHOICES = (
        ('M-Pesa', 'M-Pesa'),
        ('Cash', 'Cash'),
        ('Bank', 'Bank Transfer'),
    )

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=50, unique=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    
    # Update this line to include the choices
    method = models.CharField(max_length=50, choices=METHOD_CHOICES, default='M-Pesa') 
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.transaction_id} - {self.tenant.user.username}"
class MaintenanceRequest(models.Model):
    STATUS_CHOICES = (('pending', 'Pending'), ('assigned', 'Assigned'), ('in_progress', 'In Progress'), ('completed', 'Completed'))
    PRIORITY_CHOICES = (('high', 'High'), ('medium', 'Medium'), ('low', 'Low'))
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    issue = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='low')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    date_reported = models.DateTimeField(auto_now_add=True)
    # 1. ADD THIS NEW FIELD:
    date_resolved = models.DateTimeField(null=True, blank=True)

    # 2. ADD THIS SAVE FUNCTION:
    def save(self, *args, **kwargs):
        # Automatically set the resolved date if marked completed
        if self.status == 'completed' and not self.date_resolved:
            self.date_resolved = timezone.now()
        # If someone un-completes it, wipe the resolved date
        elif self.status != 'completed':
            self.date_resolved = None 
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.issue} ({self.tenant.user.username})"
    
class SentMessage(models.Model):
    subject = models.CharField(max_length=200)
    content = models.TextField()
    recipient_count = models.IntegerField()
    delivery_method = models.CharField(max_length=50) 
    sent_at = models.DateTimeField(auto_now_add=True)
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.subject} - {self.sent_at.strftime('%Y-%m-%d')}"