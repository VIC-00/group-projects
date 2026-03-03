from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import Property, Tenant, Payment, MaintenanceRequest, CustomUser, Announcement

# ==============================================================================
# --- 1. IDENTITY & ONBOARDING (Signup & Profile) ---
# ==============================================================================

class UserSignupForm(UserCreationForm):
    # --- 🏢 Tenant Specific Virtual Fields ---
    property_id = forms.ModelChoiceField(
        queryset=Property.objects.all(), 
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Property Name"
    )
    unit_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., A4'})
    )

    # --- 🛠️ Maintenance Specific Virtual Field ---
    target_landlord = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role='landlord'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Hiring Landlord/Agency"
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        # Included 'role' so the view knows what kind of profile to setup
        fields = ("first_name", "last_name", "username", "email", "phone_number")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get('email')
        
        # Note: 'employer' and 'role' are usually set in the view 
        # based on the POST data, but we process the base user here.
        if commit:
            user.save()
        return user

class UserUpdateForm(forms.ModelForm):
    # Explicitly defining fields ensures they are 'required' by default 
    # and prevents the NOT NULL database error.
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'})
    )
    phone_number = forms.CharField(
        required=False, # Keeping this optional as per your model
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. +254...'})
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'username', 'email', 'phone_number']


# ==============================================================================
# --- 2. PROPERTY & TENANCY MANAGEMENT ---
# ==============================================================================

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ['name', 'location', 'total_units', 'monthly_revenue', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Property Name'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Westlands, Nairobi'}),
            'total_units': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Number of Units'}),
            'monthly_revenue': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'KES'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Brief description...', 'rows': 3}),
        }

class AddTenantFullForm(forms.ModelForm):
    # These create the User Identity
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'tenant@example.com'}))
    phone_number = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}))

    class Meta:
        model = Tenant
        fields = ['assigned_property', 'unit_number', 'rent_amount', 'lease_end']
        widgets = {
            'lease_end': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'unit_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., A1, B4...'}),
            'assigned_property': forms.Select(attrs={'class': 'form-control'}),
            'rent_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'KES'}),
        }

class MoveOutRequestForm(forms.ModelForm):
    class Meta:
        model = Tenant
        # We only want the tenant to fill these two things
        fields = ['intended_move_out_date', 'move_out_reason']
        widgets = {
            'intended_move_out_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date', 
                'style': 'background: var(--bg-secondary); border: 1px solid var(--border-color); color: var(--text-primary);'
            }),
            'move_out_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Reason for moving out (e.g., job relocation, end of lease)...',
                'style': 'background: var(--bg-secondary); border: 1px solid var(--border-color); color: var(--text-primary);'
            }),
        }
        
    def clean_intended_move_out_date(self):
        move_date = self.cleaned_data.get('intended_move_out_date')
        today = timezone.now().date()
        
        # 1. Past Date Check
        if move_date and move_date < today:
            raise forms.ValidationError("The move-out date cannot be in the past.")
        
        # 2. Minimum Notice Check (Optional: e.g., 30 days)
        # notice_period = today + timezone.timedelta(days=30)
        # if move_date and move_date < notice_period:
        #     raise forms.ValidationError("Management requires at least 30 days notice.")
            
        return move_date


# ==============================================================================
# --- 3. FINANCIALS (Payment Tracking) ---
# ==============================================================================

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['tenant', 'transaction_id', 'amount', 'method', 'status']
        widgets = {
            'transaction_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction Reference'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'KES'}),
            'method': forms.Select(attrs={'class': 'form-control'}), # Will pull from Model choices
            'status': forms.Select(attrs={'class': 'form-control'}),
            'tenant': forms.Select(attrs={'class': 'form-control'}),
        }

class TenantPaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'transaction_id', 'method']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount in KES'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., RGR57TY90'}),
            'method': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'transaction_id': 'M-Pesa Code / Reference ID',
            'method': 'Payment Method'
        }


# ==============================================================================
# --- 4. OPERATIONS (Maintenance & Announcements) ---
# ==============================================================================

class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = ['tenant', 'issue', 'priority', 'status']
        widgets = {
            'tenant': forms.Select(attrs={'class': 'form-control'}),
            'issue': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

class TenantMaintenanceRequestForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        # We hide 'tenant' and 'status' because the system handles those
        fields = ['issue', 'description', 'priority'] 
        widgets = {
            'issue': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'What is the problem?'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Explain in detail...'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }

class MaintenanceAssignmentForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        # ❌ Remove 'status' from this list
        fields = ['assigned_to', 'priority'] 
        widgets = {
            'assigned_to': forms.Select(attrs={'class': 'form-control custom-select'}),
            'priority': forms.Select(attrs={'class': 'form-control custom-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(MaintenanceAssignmentForm, self).__init__(*args, **kwargs)
        
        if user:
            self.fields['assigned_to'].queryset = CustomUser.objects.filter(
                role='maintenance', 
                employer=user,
                is_active=True
            ).order_by('first_name')
        else:
            self.fields['assigned_to'].queryset = CustomUser.objects.none()

class MaintenanceTaskUpdateForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = ['status', 'tech_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'tech_notes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Explain what you fixed or if more parts are needed...'
            }),
        }

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Subject (e.g., Water Outage)',
                'style': 'background: var(--input-bg); color: var(--text-primary); border-radius: 8px;'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Details for the tenants...',
                'style': 'background: var(--input-bg); color: var(--text-primary); border-radius: 8px;'
            }),
        }