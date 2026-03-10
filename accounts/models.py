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

    employer = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='staff_team',
        limit_choices_to={'role': 'landlord'}
    )

    must_change_password = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

# ==============================================================================
# --- 2. PROPERTY ASSETS ---
# ==============================================================================

class Property(models.Model):
    landlord = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'landlord'},
        related_name='owned_properties',
        null=True,
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

    # --- 👤 Core Identity ---
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'tenant'},
        related_name='tenant_profile'
    )

    # --- 🏠 Residency Details (Strictly Required) ---
    # PROTECT ensures you can't delete a property while it still has active tenants
    assigned_property = models.ForeignKey(
        'Property', 
        on_delete=models.PROTECT,
        help_text="Building where the tenant resides."
    )
    unit_number = models.CharField(
        max_length=10,
        help_text="Specific door/unit number (e.g., A4)."
    ) 
    
    # --- 💰 Financials (Strictly Required) ---
    rent_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Monthly rent amount in KES."
    )
    balance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0
    )
    
    # --- 📅 Timeline ---
    move_in_date = models.DateField(default=timezone.now) 
    
    # ⭐ THE ONLY OPTIONAL FIELD
    lease_end = models.DateField(null=True, blank=True)
    
    # --- ⚙️ Operational Status ---
    is_active = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    
    # --- 🚪 Move-out Workflow ---
    intended_move_out_date = models.DateField(null=True, blank=True)
    move_out_reason = models.TextField(null=True, blank=True)
    
    notice_sent_at = models.DateTimeField(null=True, blank=True)
    landlord_approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        name = self.user.get_full_name() or self.user.username
        return f"{name} - {self.assigned_property.name} (Unit {self.unit_number})"

    def update_balance(self):
        """
        Calculates balance based on total time lived (from move_in_date) vs total paid.
        """
        start_date = self.move_in_date
        today = timezone.now().date()
        
        # 1. Calculation for total months inclusive of current month
        # Logic: (Years * 12) + Months + 1
        months_active = (today.year - start_date.year) * 12 + (today.month - start_date.month) + 1
        
        # Ensure we don't bill for future start dates
        if months_active < 0:
            months_active = 0
        
        # 2. Calculate Total Debt
        rent = Decimal(str(self.rent_amount))
        total_rent_due = rent * months_active
        
        # 3. Calculate Total Paid (Only 'confirmed' payments)
        total_paid_data = self.payment_set.filter(status='confirmed').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        paid = Decimal(str(total_paid_data))

        # 4. Final Balance Calculation (Arrears are positive, Credits are negative)
        self.balance = total_rent_due - paid
        self.save()

class Payment(models.Model):
    STATUS_CHOICES = (('confirmed', 'Confirmed'), ('pending', 'Pending'), ('failed', 'Failed'))
    METHOD_CHOICES = (('M-Pesa', 'M-Pesa'), ('Cash', 'Cash'), ('Bank', 'Bank Transfer'))
    
    MONTH_CHOICES = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=50, unique=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    
    for_month = models.IntegerField(choices=MONTH_CHOICES, default=timezone.now().month)
    for_year = models.IntegerField(default=timezone.now().year)
    
    method = models.CharField(max_length=50, choices=METHOD_CHOICES, default='M-Pesa') 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.tenant.user.username} - {self.get_for_month_display()} {self.for_year}"

# ==============================================================================
# --- 4. OPERATIONS (Maintenance & Comms) ---
# ==============================================================================

class MaintenanceRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),        
        ('assigned', 'Assigned'),      
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')     
    )
    
    PRIORITY_CHOICES = (('high', 'High'), ('medium', 'Medium'), ('low', 'Low'))

    # ⭐ NEW: Intelligence Categories
    CATEGORY_CHOICES = (
        ('plumbing', 'Plumbing'),
        ('electrical', 'Electrical'),
        ('carpentry', 'Carpentry/Furniture'),
        ('appliances', 'Appliances'),
        ('painting', 'Painting/Walls'),
        ('other', 'Other'),
    )
    
    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_tasks',
        limit_choices_to={'role': 'maintenance'}
    )

    issue = models.CharField(max_length=200)
    
    # ⭐ NEW: Operational Tracking
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    description = models.TextField()
    tech_notes = models.TextField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='low')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    date_reported = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    date_resolved = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.date_resolved:
            self.date_resolved = timezone.now()
        elif self.status != 'completed':
            self.date_resolved = None 
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.issue} - Unit {self.tenant.unit_number}"

class SentMessage(models.Model):
    subject = models.CharField(max_length=200)
    content = models.TextField()
    recipient_count = models.IntegerField()
    delivery_method = models.CharField(max_length=50) 
    sent_at = models.DateTimeField(auto_now_add=True)
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='announcements'
    )
    target_property = models.ForeignKey(
        'Property', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='property_announcements'
    )
    date_posted = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title