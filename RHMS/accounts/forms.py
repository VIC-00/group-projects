from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Property, Tenant, Payment, MaintenanceRequest, CustomUser

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

class UserSignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        # Removed "username" so it doesn't confuse the user
        fields = ("first_name", "last_name", "email", "phone_number")

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