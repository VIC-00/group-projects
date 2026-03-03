from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.conf import settings
from decimal import Decimal

# ==============================================================================
# --- 1. CORE IDENTITY (User Accounts) ---
# ==============================================================================

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('landlord', 'Landlord'),
        ('tenant', 'Tenant'),
        ('maintenance', 'Maintenance Staff'),
    )
    
    email = models.EmailField(unique=True, null=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='tenant')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    specialization = models.CharField(max_length=100, blank=True, null=True)

    # Link staff/tenants to a specific Landlord
    employer = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='staff_team',
        limit_choices_to={'role': 'landlord'}
    )

    # ⭐ SECURITY: Force password change on first login
    must_change_password = models.BooleanField(default=False)
    
    def __str__(self):
        # Displays: "john@email.com (Landlord)"
        return f"{self.username} ({self.get_role_display()})"

# ==============================================================================
# --- 2. PROPERTY ASSETS ---
# ==============================================================================

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


# ==============================================================================
# --- 3. TENANCY & FINANCIALS ---
# ==============================================================================

class Tenant(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('notice_given', 'Notice Given'),
        ('approved', 'Move-out Approved'),
        ('moved_out', 'Moved Out'),
    ]

    # Identity & Relationships
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'tenant'}
    )
    assigned_property = models.ForeignKey(
        'Property', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    unit_number = models.CharField(max_length=10, blank=True) 
    
    # Financials 
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Tenancy Lifecycle
    lease_end = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Move-Out Data
    intended_move_out_date = models.DateField(null=True, blank=True)
    move_out_reason = models.TextField(null=True, blank=True)
    
    # Audit Trail
    notice_sent_at = models.DateTimeField(null=True, blank=True)
    landlord_approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ⭐ THE FIX: Removes "Tenant object (6)" from dropdowns
    def __str__(self):
        name = self.user.get_full_name() or self.user.username
        return f"{name} - Unit {self.unit_number}"

    # --- Financial Logic ---
    def update_balance(self):
        """
        Calculates the true balance: 
        Current Rent - Total Confirmed Payments
        """
        # assumes your Payment model has a foreign key to 'tenant'
        total_paid = self.payment_set.filter(status='confirmed').aggregate(
            total=Sum('amount'))['total'] or 0
        
        rent = Decimal(self.rent_amount or 0)
        paid = Decimal(total_paid)
        
        self.balance = rent - paid
        self.save()
    

class Payment(models.Model):
    STATUS_CHOICES = (('confirmed', 'Confirmed'), ('pending', 'Pending'), ('failed', 'Failed'))
    
    METHOD_CHOICES = (
        ('M-Pesa', 'M-Pesa'),
        ('Cash', 'Cash'),
        ('Bank', 'Bank Transfer'),
    )

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=50, unique=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    
    # Update this line to include the choices
    method = models.CharField(max_length=50, choices=METHOD_CHOICES, default='M-Pesa') 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.transaction_id} - {self.tenant.user.username}"


# ==============================================================================
# --- 4. OPERATIONS (Maintenance & Comms) ---
# ==============================================================================

class MaintenanceRequest(models.Model):
    # 1. Choices for Status and Priority
    STATUS_CHOICES = (
        ('pending', 'Pending'),        
        ('assigned', 'Assigned'),      
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')     
    )
    
    PRIORITY_CHOICES = (
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low')
    )
    
    # 2. Core Relationship Fields
    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE)
    
    # The "Who": Links to the technician (User with role='maintenance')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_tasks',
        limit_choices_to={'role': 'maintenance'}
    )

    # 3. Task Details
    issue = models.CharField(max_length=200)
    description = models.TextField()
    
    # 4. Technician Feedback Fields
    tech_notes = models.TextField(null=True, blank=True)
    
    # 5. Tracking and Status
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='low')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # 6. Timestamps
    date_reported = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    date_resolved = models.DateTimeField(null=True, blank=True)

    # 7. Logic: Automatically handle resolution timestamps
    def save(self, *args, **kwargs):
        # If the status is being changed to completed, set the date_resolved
        if self.status == 'completed' and not self.date_resolved:
            self.date_resolved = timezone.now()
        # If a completed task is reopened for some reason, clear the resolved date
        elif self.status != 'completed':
            self.date_resolved = None 
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.issue} - Unit {self.tenant.unit_number} ({self.status})"


class SentMessage(models.Model):
    subject = models.CharField(max_length=200)
    content = models.TextField()
    recipient_count = models.IntegerField()
    delivery_method = models.CharField(max_length=50) 
    sent_at = models.DateTimeField(auto_now_add=True)
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.subject} - {self.sent_at.strftime('%Y-%m-%d')}"
    

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    date_posted = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True) 

    def __str__(self):
        return self.title