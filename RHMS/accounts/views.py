import csv
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout 
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.db.models import Sum, Count, Q, Avg, F
from .models import Property, Tenant, Payment, MaintenanceRequest, CustomUser, SentMessage
from .forms import PropertyForm, AddTenantFullForm, UserSignupForm, PaymentForm, MaintenanceForm
from django.urls import reverse
from django.http import HttpResponse
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from django.db import IntegrityError

# --- 1. MASTER AUTHENTICATION (Login & Signup) ---
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        # --- FLEXIBLE SIGNUP ---
        if 'signup_submit' in request.POST:
            form = UserSignupForm(request.POST)
            if form.is_valid():
                # We pull whatever they typed in the signup box
                # In your HTML this is likely named 'email' or 'username'
                raw_id = form.cleaned_data.get('email') or request.POST.get('username')
                
                user = form.save(commit=False)
                user.username = raw_id # Pushes the exact text to the Admin Username column
                user.email = raw_id    # Pushes the exact text to the Admin Email column
                user.role = 'landlord'
                user.save() 
                
                login(request, user)
                return redirect('dashboard')

        # --- SMART DUAL LOGIN ---
        else:
            # Grabs whatever was typed in the 'Sign In' box
            identifier = request.POST.get('username') 
            pass_word = request.POST.get('password')

            # Search for a match in EITHER the Username OR Email columns
            user_obj = CustomUser.objects.filter(Q(username=identifier) | Q(email=identifier)).first()

            if user_obj:
                # Use the official username found in the database to authenticate
                user = authenticate(request, username=user_obj.username, password=pass_word)
                if user is not None:
                    login(request, user)
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Incorrect password.')
            else:
                messages.error(request, 'User not found. Check your details.')

    return render(request, 'login.html', {'form': UserSignupForm()})

def logout_view(request):
    logout(request)
    return redirect('login')

# --- 2. DASHBOARD ---
@login_required(login_url='login') 
def dashboard_view(request):
    # Isolate properties owned by the current landlord
    my_properties = Property.objects.filter(landlord=request.user)

    recent_payments = Payment.objects.filter(
        tenant__assigned_property__in=my_properties
    ).select_related('tenant__user').order_by('-date')[:5]

    recent_requests = MaintenanceRequest.objects.filter(
        tenant__assigned_property__in=my_properties
    ).select_related('tenant__user').order_by('-date_reported')[:5]

    # --- Chart Data Prep ---
    prop_names = []
    prop_revenues = []
    
    for p in my_properties:
        prop_names.append(p.name)
        collected = Payment.objects.filter(
            tenant__assigned_property=p, 
            status='confirmed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        prop_revenues.append(float(collected))

    pending_count = MaintenanceRequest.objects.filter(tenant__assigned_property__in=my_properties, status='pending').count()
    progress_count = MaintenanceRequest.objects.filter(tenant__assigned_property__in=my_properties, status='in_progress').count()
    completed_count = MaintenanceRequest.objects.filter(tenant__assigned_property__in=my_properties, status='completed').count()

    context = {
        'total_properties': my_properties.count(),
        'active_tenants': Tenant.objects.filter(assigned_property__in=my_properties).count(),
        'total_rent': f"{Payment.objects.filter(tenant__assigned_property__in=my_properties, status='confirmed').aggregate(Sum('amount'))['amount__sum'] or 0:,.0f}",
        'pending_maintenance': pending_count,
        'recent_payments': recent_payments,
        'recent_requests': recent_requests,
        'prop_names': prop_names,
        'prop_revenues': prop_revenues,
        'maint_data': [pending_count, progress_count, completed_count],
    }
    return render(request, 'dashboard.html', context)

# --- 3. PROPERTIES ---
@login_required(login_url='login')
def properties_view(request):
    my_properties = Property.objects.filter(landlord=request.user)
    
    query = request.GET.get('q', '')
    if query:
        properties = my_properties.filter(
            Q(name__icontains=query) | Q(location__icontains=query)
        )
    else:
        properties = my_properties

    total_units = properties.aggregate(Sum('total_units'))['total_units__sum'] or 0
    occupied = Tenant.objects.filter(assigned_property__in=properties).count()
    total_revenue = properties.aggregate(Sum('monthly_revenue'))['monthly_revenue__sum'] or 0
    
    context = {
        'properties': properties,
        'total_properties': properties.count(),
        'occupied_units': occupied,
        'vacant_units': total_units - occupied,
        'total_portfolio_value': f"{total_revenue:,.0f}",
        'query': query,
    }
    return render(request, 'properties.html', context)

# --- 4. TENANTS ---
@login_required(login_url='login')
def tenants_view(request):
    search_query = request.GET.get('q', '')
    property_filter = request.GET.get('property_id', 'all')

    # Filter tenants through the property relationship
    tenants = Tenant.objects.filter(assigned_property__landlord=request.user).select_related('user', 'assigned_property')

    if property_filter != 'all':
        tenants = tenants.filter(assigned_property_id=property_filter)
    
    if search_query:
        tenants = tenants.filter(
            Q(user__first_name__icontains=search_query) | 
            Q(user__last_name__icontains=search_query) |
            Q(unit_number__icontains=search_query)
        )

    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    
    move_outs_count = tenants.filter(lease_end__gte=start_of_month, lease_end__lt=next_month).count()

    context = {
        'tenants': tenants,
        'properties': Property.objects.filter(landlord=request.user),
        'standing_count': tenants.filter(balance=0).count(),
        'overdue_count': tenants.filter(balance__gt=0).count(),
        'move_outs_count': move_outs_count,
        'query': search_query,
        'selected_property': property_filter,
    }
    return render(request, 'tenants.html', context)

# --- 5. PAYMENTS ---
@login_required(login_url='login')
def payments_view(request):
    status_filter = request.GET.get('status', 'all')
    month_filter = request.GET.get('month', timezone.now().strftime('%Y-%m'))

    payments = Payment.objects.filter(tenant__assigned_property__landlord=request.user).select_related('tenant__user', 'tenant__assigned_property').order_by('-date')

    if status_filter != 'all':
        payments = payments.filter(status=status_filter)
    
    if month_filter:
        year, month = map(int, month_filter.split('-'))
        payments = payments.filter(date__year=year, date__month=month)

    total_collected = payments.filter(status='confirmed').aggregate(Sum('amount'))['amount__sum'] or 0
    total_pending = payments.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0
    expected = Property.objects.filter(landlord=request.user).aggregate(Sum('monthly_revenue'))['monthly_revenue__sum'] or 0
    rate = (total_collected / expected * 100) if expected > 0 else 0

    context = {
        'payments': payments,
        'total_collected': f"{total_collected:,.0f}",
        'total_pending': f"{total_pending:,.0f}",
        'expected_total': f"{expected:,.0f}",
        'collection_rate': round(rate, 1),
        'selected_status': status_filter,
        'selected_month': month_filter,
    }
    return render(request, 'payments.html', context)

# --- 6. MAINTENANCE ---
@login_required(login_url='login')
def maintenance_view(request):
    status_filter = request.GET.get('status', 'all')
    requests = MaintenanceRequest.objects.filter(tenant__assigned_property__landlord=request.user).select_related('tenant__user', 'tenant__assigned_property').order_by('-date_reported')

    if status_filter != 'all':
        requests = requests.filter(status=status_filter)

    open_count = requests.filter(status='pending').count()
    progress_count = requests.filter(status='in_progress').count()
    completed_count = requests.filter(status='completed').count()

    resolved_tasks = requests.filter(status='completed', date_resolved__isnull=False)
    avg_timedelta = resolved_tasks.aggregate(avg_time=Avg(F('date_resolved') - F('date_reported')))['avg_time']
    
    if avg_timedelta:
        days = avg_timedelta.days
        avg_display = f"{days} Days" if days > 0 else "Under 24h"
    else:
        avg_display = "---"

    context = {
        'maintenance_requests': requests,
        'open_count': open_count,
        'progress_count': progress_count,
        'completed_count': completed_count,
        'avg_resolution': avg_display,
        'selected_status': status_filter,
    }
    return render(request, 'maintenance.html', context)

# --- 7. REPORTS & SETTINGS ---
@login_required(login_url='login')
def reports_view(request):
    my_properties = Property.objects.filter(landlord=request.user)
    prop_data = []
    for p in my_properties:
        collected = Payment.objects.filter(tenant__assigned_property=p, status='confirmed').aggregate(Sum('amount'))['amount__sum'] or 0
        tenant_count = p.tenant_set.count()
        occ_percent = (tenant_count / p.total_units * 100) if p.total_units > 0 else 0
        
        prop_data.append({
            'name': p.name,
            'target': p.monthly_revenue,
            'collected': collected,
            'shortfall': p.monthly_revenue - collected,
            'occupancy': occ_percent,
            'total_units': p.total_units,
            'vacant': p.total_units - tenant_count
        })

    context = {
        'prop_data': prop_data,
        'open_tasks': MaintenanceRequest.objects.filter(tenant__assigned_property__landlord=request.user, status='pending').count(),
        'completed_tasks': MaintenanceRequest.objects.filter(tenant__assigned_property__landlord=request.user, status='completed').count(),
        'total_confirmed': Payment.objects.filter(tenant__assigned_property__landlord=request.user, status='confirmed').aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_arrears': Tenant.objects.filter(assigned_property__landlord=request.user).aggregate(Sum('balance'))['balance__sum'] or 0,
        'overdue_tenants': Tenant.objects.filter(assigned_property__landlord=request.user, balance__gt=0).select_related('user', 'assigned_property'),
    }
    return render(request, 'reports.html', context)

@login_required(login_url='login')
def settings_view(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.phone_number = request.POST.get('phone_number')
        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('settings')
    return render(request, 'settings.html')

# --- 8. ADD DATA VIEWS ---
@login_required(login_url='login')
def add_property(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            property_obj = form.save(commit=False)
            property_obj.landlord = request.user # Automated ownership
            property_obj.save()
            messages.success(request, 'Property added successfully')
            return redirect('properties')
    else:
        form = PropertyForm()
    return render(request, 'add_property.html', {'form': form})

@login_required(login_url='login')
def add_tenant(request):
    if request.method == 'POST':
        form = AddTenantFullForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, "User with this email already exists")
                return render(request, 'add_tenant.html', {'form': form})

            user = CustomUser.objects.create(
                username=email, email=email,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                phone_number=form.cleaned_data['phone_number'],
                role='tenant'
            )
            user.set_password("Welcome@2026") 
            user.save()

            tenant = form.save(commit=False)
            tenant.user = user
            tenant.balance = tenant.rent_amount 
            tenant.save()
            
            messages.success(request, f'Tenant account created for {user.get_full_name()}')
            return redirect('tenants')
    else:
        form = AddTenantFullForm()
        # Filter dropdown to only show THIS landlord's properties
        form.fields['assigned_property'].queryset = Property.objects.filter(landlord=request.user)
    return render(request, 'add_tenant.html', {'form': form})

@login_required(login_url='login')
def record_payment(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save()
            if payment.status == 'confirmed':
                tenant = payment.tenant
                tenant.balance -= payment.amount
                tenant.save()
            messages.success(request, f'Payment recorded for {payment.tenant.user.get_full_name()}')
            return redirect('payments')
    else:
        form = PaymentForm()
        # Ensure only this landlord's tenants appear in the form
        form.fields['tenant'].queryset = Tenant.objects.filter(assigned_property__landlord=request.user)
    return render(request, 'record_payment.html', {'form': form})

@login_required(login_url='login')
def add_maintenance(request):
    if request.method == 'POST':
        form = MaintenanceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('maintenance')
    else:
        form = MaintenanceForm()
        form.fields['tenant'].queryset = Tenant.objects.filter(assigned_property__landlord=request.user)
    return render(request, 'add_maintenance.html', {'form': form, 'edit_mode': False})

# --- 9. EDIT / DELETE VIEWS (With Ownership Validation) ---
@login_required(login_url='login')
def edit_property(request, pk):
    property_obj = get_object_or_404(Property, pk=pk, landlord=request.user)
    if request.method == 'POST':
        form = PropertyForm(request.POST, instance=property_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Updated {property_obj.name} successfully')
            return redirect('properties')
    else:
        form = PropertyForm(instance=property_obj)
    return render(request, 'edit_property.html', {'form': form, 'property': property_obj})

@login_required(login_url='login')
def delete_property(request, pk):
    property_obj = get_object_or_404(Property, pk=pk, landlord=request.user)
    if request.method == 'POST':
        name = property_obj.name
        property_obj.delete()
        messages.success(request, f"Property {name} deleted successfully.")
        return redirect('properties')
    return render(request, 'confirm_delete.html', {'obj': property_obj.name, 'type': 'property', 'back_url': reverse('properties')})

@login_required(login_url='login')
def edit_tenant(request, pk):
    tenant = get_object_or_404(Tenant, pk=pk, assigned_property__landlord=request.user)
    user = tenant.user
    if request.method == 'POST':
        form = AddTenantFullForm(request.POST, instance=tenant)
        if form.is_valid():
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.phone_number = form.cleaned_data['phone_number']
            user.save()
            form.save()
            messages.success(request, f"Tenant {user.get_full_name()} updated successfully")
            return redirect('tenants')
    else:
        initial_data = {'first_name': user.first_name, 'last_name': user.last_name, 'email': user.email, 'phone_number': user.phone_number}
        form = AddTenantFullForm(instance=tenant, initial=initial_data)
        form.fields['assigned_property'].queryset = Property.objects.filter(landlord=request.user)
    return render(request, 'edit_tenant.html', {'form': form, 'tenant': tenant})

@login_required(login_url='login')
def delete_tenant(request, pk):
    tenant = get_object_or_404(Tenant, pk=pk, assigned_property__landlord=request.user)
    user = tenant.user
    if request.method == 'POST':
        tenant_name = user.get_full_name()
        user.delete() 
        messages.success(request, f"Tenant {tenant_name} has been removed.")
        return redirect('tenants')
    return render(request, 'confirm_delete.html', {'obj': user.get_full_name(), 'type': 'tenant and user account', 'back_url': reverse('tenants')})

@login_required(login_url='login')
def edit_payment(request, pk):
    payment = get_object_or_404(Payment, pk=pk, tenant__assigned_property__landlord=request.user)
    tenant = payment.tenant
    old_amount = payment.amount if payment.status == 'confirmed' else 0

    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            new_payment = form.save(commit=False)
            if new_payment.status == 'confirmed':
                new_amount = new_payment.amount
                tenant.balance += old_amount
                tenant.balance -= new_amount
                tenant.save()
            elif payment.status != 'confirmed' and old_amount > 0:
                tenant.balance += old_amount
                tenant.save()
            new_payment.save()
            messages.success(request, f"Payment for {tenant.user.get_full_name()} updated")
            return redirect('payments')
    else:
        form = PaymentForm(instance=payment)
        form.fields['tenant'].queryset = Tenant.objects.filter(assigned_property__landlord=request.user)
    return render(request, 'record_payment.html', {'form': form, 'edit_mode': True, 'payment': payment})

@login_required(login_url='login')
def delete_payment(request, pk):
    payment = get_object_or_404(Payment, pk=pk, tenant__assigned_property__landlord=request.user)
    tenant = payment.tenant
    if request.method == 'POST':
        if payment.status == 'confirmed':
            tenant.balance += payment.amount
            tenant.save()
        payment.delete()
        messages.success(request, "Payment record deleted and balance adjusted")
        return redirect('payments')
    return render(request, 'confirm_delete.html', {'obj': f"Payment of KES {payment.amount}", 'type': 'payment record', 'back_url': reverse('payments')})

@login_required(login_url='login')
def edit_maintenance(request, pk):
    maintenance_req = get_object_or_404(MaintenanceRequest, pk=pk, tenant__assigned_property__landlord=request.user)
    if request.method == 'POST':
        form = MaintenanceForm(request.POST, instance=maintenance_req)
        if form.is_valid():
            form.save()
            return redirect('maintenance')
    else:
        form = MaintenanceForm(instance=maintenance_req)
        form.fields['tenant'].queryset = Tenant.objects.filter(assigned_property__landlord=request.user)
    return render(request, 'add_maintenance.html', {'form': form, 'edit_mode': True})

@login_required(login_url='login')
def delete_maintenance(request, pk):
    maintenance_req = get_object_or_404(MaintenanceRequest, pk=pk, tenant__assigned_property__landlord=request.user)
    if request.method == 'POST':
        maintenance_req.delete()
        messages.success(request, "Maintenance request deleted.")
        return redirect('maintenance')
    return render(request, 'confirm_delete.html', {'obj': f"Request #MNT-{maintenance_req.id}", 'back_url': 'maintenance'})

# --- 10. EXPORTS (Isolated) ---
@login_required(login_url='login')
def export_revenue_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="revenue_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Property', 'Monthly Target', 'Collected', 'Shortfall', 'Occupancy %'])
    for p in Property.objects.filter(landlord=request.user):
        collected = Payment.objects.filter(tenant__assigned_property=p, status='confirmed').aggregate(Sum('amount'))['amount__sum'] or 0
        occ = (p.tenant_set.count()/p.total_units*100) if p.total_units > 0 else 0
        writer.writerow([p.name, p.monthly_revenue, collected, p.monthly_revenue - collected, occ])
    return response

@login_required(login_url='login')
def export_arrears_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tenant_arrears.csv"'
    writer = csv.writer(response)
    writer.writerow(['Tenant', 'Property', 'Unit', 'Phone', 'Balance Due'])
    for t in Tenant.objects.filter(assigned_property__landlord=request.user, balance__gt=0):
        writer.writerow([t.user.get_full_name(), t.assigned_property.name, t.unit_number, f"'{t.user.phone_number}", t.balance])
    return response

@login_required(login_url='login')
def export_tenants_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="full_tenant_list.csv"'
    writer = csv.writer(response)
    writer.writerow(['Name', 'Property', 'Unit', 'Phone', 'Balance'])
    for t in Tenant.objects.filter(assigned_property__landlord=request.user).select_related('user', 'assigned_property'):
        writer.writerow([t.user.get_full_name(), t.assigned_property.name, t.unit_number, f"'{t.user.phone_number}", t.balance])
    return response

@login_required(login_url='login')
def export_properties_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="properties_export.csv"'
    writer = csv.writer(response)
    writer.writerow(['Property Name', 'Location', 'Units', 'Revenue'])
    for p in Property.objects.filter(landlord=request.user):
        writer.writerow([p.name, p.location, p.total_units, p.monthly_revenue])
    return response

@login_required(login_url='login')
def export_payments_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payments_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Transaction ID', 'Tenant', 'Amount', 'Date', 'Status'])
    for p in Payment.objects.filter(tenant__assigned_property__landlord=request.user):
        writer.writerow([p.transaction_id, p.tenant.user.get_full_name(), p.amount, p.date, p.status])
    return response

@login_required(login_url='login')
def export_maintenance_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="maintenance_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Request ID', 'Tenant', 'Property', 'Unit', 'Issue', 'Priority', 'Date Reported', 'Status'])
    requests = MaintenanceRequest.objects.filter(tenant__assigned_property__landlord=request.user).select_related('tenant__user', 'tenant__assigned_property')
    for req in requests:
        writer.writerow([f"#MNT-{req.id}", req.tenant.user.get_full_name(), req.tenant.assigned_property.name, req.tenant.unit_number, req.issue, req.priority.title(), req.date_reported.strftime("%Y-%m-%d"), req.status.title()])
    return response

# --- 11. EXTRA UTILITIES ---
@login_required(login_url='login')
def send_mass_message(request):
    if request.method == 'POST':
        group = request.POST.get('recipient_group')
        subject = request.POST.get('subject')
        content = request.POST.get('message_content')
        methods = request.POST.getlist('delivery_method')

        tenants = Tenant.objects.filter(assigned_property__landlord=request.user)
        
        if group == 'overdue':
            tenants = tenants.filter(balance__gt=0)
        elif group == 'specific':
            tenant_id = request.POST.get('specific_tenant_id')
            tenants = tenants.filter(id=tenant_id)

        for tenant in tenants:
            personalized_msg = content.replace("{tenant_name}", tenant.user.get_full_name())
            if 'sms' in methods: print(f"DEBUG: SMS sent to {tenant.user.phone_number}")
            if 'email' in methods: print(f"DEBUG: Email sent to {tenant.user.email}")

        SentMessage.objects.create(subject=subject, content=content, recipient_count=tenants.count(), delivery_method=", ".join(methods), sender=request.user)
        messages.success(request, f"Mass message sent to {tenants.count()} tenants!")
        return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required(login_url='login')
def property_detail(request, pk):
    property_obj = get_object_or_404(Property, pk=pk, landlord=request.user)
    tenants = Tenant.objects.filter(assigned_property=property_obj).select_related('user')
    return render(request, 'property_detail.html', {'property': property_obj, 'tenants': tenants})

@login_required(login_url='login')
def import_properties(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            reader.fieldnames = [field.strip().lower() for field in reader.fieldnames]
            count = 0
            for row in reader:
                Property.objects.create(
                    landlord=request.user,
                    name=row.get('name') or row.get('property name'),
                    location=row.get('location'),
                    total_units=row.get('total_units') or 0,
                    monthly_revenue=row.get('monthly_revenue') or 0.00,
                    description=row.get('description', '')
                )
                count += 1
            messages.success(request, f"Successfully imported {count} properties.")
            return redirect('properties')
        except Exception as e:
            messages.error(request, f"Import failed: {str(e)}")
            return redirect('import_properties')
    return render(request, 'import_properties.html')

@login_required(login_url='login')
def generate_invoice(request, pk):
    payment = get_object_or_404(Payment, pk=pk, tenant__assigned_property__landlord=request.user)
    return render(request, 'invoice.html', {'payment': payment})