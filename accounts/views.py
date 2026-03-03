import csv
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout,update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Sum, Count, Q, Avg, F
from .models import Property, Tenant, Payment, MaintenanceRequest, CustomUser, SentMessage, Announcement
from .forms import PropertyForm, AddTenantFullForm, UserSignupForm, PaymentForm, MaintenanceForm, TenantMaintenanceRequestForm, AnnouncementForm, MoveOutRequestForm, UserUpdateForm,TenantPaymentForm, MaintenanceTaskUpdateForm, MaintenanceAssignmentForm
from django.urls import reverse
from django.http import HttpResponse
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from django.db import IntegrityError
from decimal import Decimal, InvalidOperation

# ==============================================================================
# --- 1. MASTER AUTHENTICATION & PROFILE SETTINGS ---
# ==============================================================================

# --- 1. MASTER AUTHENTICATION (Login & Signup) ---
def login_view(request):
    if request.user.is_authenticated:
        if request.user.role == 'tenant':
            return redirect('tenant_dashboard')
        elif request.user.role == 'maintenance':
            return redirect('maintenance_dashboard')
        else:
            return redirect('dashboard')

    if request.method == 'POST':
        # --- SIGNUP LOGIC ---
        if 'signup_submit' in request.POST:
            form = UserSignupForm(request.POST)
            if form.is_valid():
                user = form.save(commit=False)
                selected_role = request.POST.get('role_selection') 
                
                # 🏠 CASE: TENANT
                if selected_role == 'tenant':
                    user.role = 'tenant'
                    user.save()
                    Tenant.objects.create(
                        user=user,
                        assigned_property_id=request.POST.get('property_id'),
                        unit_number=request.POST.get('unit_number'),
                        status='pending',
                        rent_amount=0
                    )
                    messages.success(request, "Tenant account created! Please wait for management approval.")
                    return redirect('login')
                
                # 🛠️ CASE: MAINTENANCE STAFF (Fixed with Employer Logic)
                elif selected_role == 'maintenance':
                    user.role = 'maintenance'
                    user.is_active = False  
                    user.specialization = request.POST.get('specialization')
                    
                    # ⭐ LINK TO TARGET LANDLORD
                    target_landlord_id = request.POST.get('target_landlord')
                    if target_landlord_id:
                        user.employer_id = target_landlord_id
                    
                    user.save()
                    messages.success(request, "Staff registration received. Your target landlord will review your application.")
                    return redirect('login')
                
                # 🔑 CASE: LANDLORD
                else:
                    user.role = 'landlord'
                    user.save()
                    login(request, user)
                    messages.success(request, "Landlord account created successfully!")
                    return redirect('dashboard')
            else:
                for field, errors in form.errors.items():
                    messages.error(request, f"{field.replace('_', ' ').title()}: {errors[0]}")

        # --- LOGIN LOGIC ---
        else:
            identifier = request.POST.get('username')
            pass_word = request.POST.get('password')
            user_obj = CustomUser.objects.filter(Q(username=identifier) | Q(email=identifier)).first()

            if user_obj:
                if not user_obj.is_active and user_obj.role == 'maintenance':
                    messages.warning(request, "Your staff account is still awaiting approval.")
                    return redirect('login')

                user = authenticate(request, username=user_obj.username, password=pass_word)
                if user is not None:
                    if user.role == 'tenant':
                        tenant_profile = Tenant.objects.filter(user=user).first()
                        if tenant_profile and tenant_profile.status == 'pending':
                            messages.warning(request, "Tenant approval pending.")
                            return redirect('login')
                    
                    login(request, user)
                    if user.role == 'tenant': return redirect('tenant_dashboard')
                    elif user.role == 'maintenance': return redirect('maintenance_dashboard')
                    else: return redirect('dashboard')
                else:
                    messages.error(request, "Incorrect password.")
            else:
                messages.error(request, "User account not found.")

    # ⭐ ADDED LANDLORDS TO CONTEXT
    return render(request, 'login.html', {
        'form': UserSignupForm(),
        'properties': Property.objects.all(),
        'landlords': CustomUser.objects.filter(role='landlord')
    })

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def profile_settings(request):
    """
    Handles both profile information updates and secure password changes 
    on a single page for the logged-in user.
    """
    if request.method == 'POST':
        # 1. Handle Profile Info Update (First Name, Email, Phone, etc.)
        if 'update_profile' in request.POST:
            profile_form = UserUpdateForm(request.POST, instance=request.user)
            # Initialize the password form so it's available in the context if validation fails
            password_form = PasswordChangeForm(request.user)
            
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Your profile details have been updated!')
                return redirect('profile_settings')
            else:
                messages.error(request, 'Please correct the profile errors below.')
        
        # 2. Handle Password Change using Django's built-in validation
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            # Initialize the profile form so it's available in the context if validation fails
            profile_form = UserUpdateForm(instance=request.user)
            
            if password_form.is_valid():
                user = password_form.save()
                # 💡 Keeps the user logged in by updating the session hash
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password was successfully updated!')
                return redirect('profile_settings')
            else:
                messages.error(request, 'Password change failed. See errors below.')

    # If GET request, pre-fill forms with current user data
    else:
        profile_form = UserUpdateForm(instance=request.user)
        password_form = PasswordChangeForm(request.user)

    return render(request, 'profile_settings.html', {
        'profile_form': profile_form,
        'password_form': password_form,
        'tenant': getattr(request.user, 'tenant_profile', None) # Useful if you need tenant-specific info
    })

@login_required(login_url='login')
def settings_view(request):
    user = request.user
    
    if request.method == 'POST':
        # --- 1. Handle Profile Update ---
        if 'update_profile' in request.POST:
            user.first_name = request.POST.get('first_name')
            user.last_name = request.POST.get('last_name')
            user.username = request.POST.get('username')
            user.email = request.POST.get('email')
            user.phone_number = request.POST.get('phone_number')
            
            if not user.first_name or not user.last_name:
                messages.error(request, "First and Last names are required.")
            else:
                user.save()
                messages.success(request, "Profile updated successfully!")
            return redirect('settings')

        # --- 2. Handle Password Change ---
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user, request.POST)
            
            if password_form.is_valid():
                # Custom Check: Ensure the new password isn't the same as the old one
                new_password = password_form.cleaned_data.get('new_password1')
                if user.check_password(new_password):
                    messages.error(request, "New password cannot be the same as your old password.")
                else:
                    user = password_form.save()
                    update_session_auth_hash(request, user) # Prevents logout
                    messages.success(request, "Password updated successfully!")
                    return redirect('settings')
            else:
                # If form is invalid (mismatch, too short, etc.), Django adds errors to password_form
                messages.error(request, "Please correct the password errors below.")

    # GET Request
    else:
        password_form = PasswordChangeForm(user)

    return render(request, 'settings.html', {'password_form': password_form})


# ==============================================================================
# --- 2. LANDLORD DASHBOARD & MASTER VIEWS ---
# ==============================================================================

# --- 2. DASHBOARD ---
@login_required(login_url='login') 
def dashboard_view(request):
    if request.user.role != 'landlord':
        return redirect('tenant_dashboard')

    my_properties = Property.objects.filter(landlord=request.user)
    
    # 1. Move-Out Logic
    move_out_notices = Tenant.objects.filter(
        assigned_property__in=my_properties, 
        status='notice_given'
    ).count()

    # 2. Announcement Logic
    if request.method == 'POST' and 'post_announcement' in request.POST:
        announcement_form = AnnouncementForm(request.POST)
        if announcement_form.is_valid():
            announcement_form.save()
            messages.success(request, "Announcement broadcasted!")
            return redirect('dashboard')
    else:
        announcement_form = AnnouncementForm()

    # 3. Chart Data Preparation (The Missing Piece)
    # --- Revenue by Property ---
    prop_names = []
    prop_revenues = []
    for prop in my_properties:
        prop_names.append(prop.name)
        # Sum confirmed payments for THIS specific property
        revenue = Payment.objects.filter(
            tenant__assigned_property=prop, 
            status='confirmed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        prop_revenues.append(float(revenue)) # Convert to float for JSON

    # --- Maintenance Status Doughnut ---
    maint_requests = MaintenanceRequest.objects.filter(tenant__assigned_property__in=my_properties)
    pending_count = maint_requests.filter(status='pending').count()
    progress_count = maint_requests.filter(status='in_progress').count()
    completed_count = maint_requests.filter(status='completed').count()
    
    # This list corresponds to the labels in your JS: ['Pending', 'In Progress', 'Completed']
    maint_data = [pending_count, progress_count, completed_count]

    # 4. Recent Tables
    recent_payments = Payment.objects.filter(
        tenant__assigned_property__in=my_properties
    ).select_related('tenant__user', 'tenant__assigned_property').order_by('-date')[:5]

    recent_requests = MaintenanceRequest.objects.filter(
        tenant__assigned_property__in=my_properties
    ).select_related('tenant__user', 'tenant__assigned_property').order_by('-date_reported')[:5]

    # 5. Final Context
    context = {
        'total_properties': my_properties.count(),
        'active_tenants': Tenant.objects.filter(assigned_property__in=my_properties, status='active').count(),
        'move_out_notices': move_out_notices,
        'total_rent': f"{sum(prop_revenues):,.0f}", # Calculate total from our chart list
        'pending_maintenance': pending_count,
        'recent_payments': recent_payments,
        'recent_requests': recent_requests,
        'announcement_form': announcement_form,
        
        # 📊 ADD THESE TO FIX THE CHARTS
        'prop_names': prop_names,
        'prop_revenues': prop_revenues,
        'maint_data': maint_data,
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

    # Base queryset for all tenants linked to this landlord
    all_landlord_tenants = Tenant.objects.filter(assigned_property__landlord=request.user).select_related('user', 'assigned_property')

    # 1. NEW SIGNUPS: Filter for those in 'pending' status
    pending_tenants = all_landlord_tenants.filter(status='pending')

    # 2. MAIN DIRECTORY: Filter for those already approved/active
    # We exclude 'pending' so they don't clutter your main management table
    tenants = all_landlord_tenants.exclude(status='pending')

    # Apply search and property filters to the main list
    if property_filter != 'all':
        tenants = tenants.filter(assigned_property_id=property_filter)
    
    if search_query:
        tenants = tenants.filter(
            Q(user__first_name__icontains=search_query) | 
            Q(user__last_name__icontains=search_query) |
            Q(unit_number__icontains=search_query)
        )

    # Workflow Counters
    # This matches the names used in your tenants.html stat cards
    move_out_notices = tenants.filter(status='notice_given').count()
    standing_count = tenants.filter(balance=0, status='active').count()
    overdue_count = tenants.filter(balance__gt=0, status='active').count()

    context = {
        'tenants': tenants,
        'pending_tenants': pending_tenants, # 🆕 Send these to the template
        'properties': Property.objects.filter(landlord=request.user),
        'standing_count': standing_count,
        'overdue_count': overdue_count,
        'move_out_notices': move_out_notices, # 🆕 Added for your orange stat card
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
    # Ensure only landlords can access this view
    if request.user.role != 'landlord':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    status_filter = request.GET.get('status', 'all')
    
    # 1. Fetch Maintenance Tasks (Filtered by properties owned by THIS landlord)
    requests = MaintenanceRequest.objects.filter(
        tenant__assigned_property__landlord=request.user
    ).select_related(
        'tenant__user', 
        'tenant__assigned_property', 
        'assigned_to'
    ).order_by('-date_reported')

    # Apply status filter if selected
    if status_filter != 'all':
        requests = requests.filter(status=status_filter)

    # --- 🏗️ THE NOTIFICATION FIX ---
    # Only count unapproved maintenance staff who specifically applied to THIS landlord
    pending_staff_count = CustomUser.objects.filter(
        role='maintenance', 
        is_active=False,
        employer=request.user  # ✅ This prevents the "leak" to other landlords
    ).count()

    # 2. Stats Calculations (Filtered to this landlord's tasks)
    open_count = requests.filter(status='pending').count()
    progress_count = requests.filter(status='in_progress').count()
    completed_count = requests.filter(status='completed').count()

    # 3. Calculate Average Resolution Time
    resolved_tasks = requests.filter(status='completed', date_resolved__isnull=False)
    avg_timedelta = resolved_tasks.aggregate(
        avg_time=Avg(F('date_resolved') - F('date_reported'))
    )['avg_time']
    
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
        'pending_staff_count': pending_staff_count, # Red badge count
    }
    
    return render(request, 'maintenance.html', context)

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


# ==============================================================================
# --- 3. TENANT PORTAL VIEWS ---
# ==============================================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Tenant, Announcement, Payment, MaintenanceRequest
from .forms import MoveOutRequestForm  # 👈 Don't forget to import your form!

@login_required(login_url='login')
def tenant_dashboard(request):
    # 1. Password Security Guard
    if request.user.must_change_password:
        messages.info(request, "For your security, please update your password.")
        return redirect('change_password')

    # 2. Role Check
    if request.user.role != 'tenant':
        return redirect('dashboard')
    
    tenant_profile = get_object_or_404(Tenant, user=request.user)

    # 3. Approval Gatekeeper
    if tenant_profile.status == 'pending':
        return render(request, 'tenants/pending_approval.html', {'tenant': tenant_profile})
    
    # --- 4. HANDLE WORKFLOW LOGIC (POST) ---
    if request.method == 'POST':
        
        # 🚪 SUBMIT MOVE-OUT NOTICE
        if 'submit_move_out' in request.POST:
            # We pass 'instance' so it updates the EXISTING tenant profile
            form = MoveOutRequestForm(request.POST, instance=tenant_profile)
            if form.is_valid():
                notice = form.save(commit=False)
                notice.status = 'notice_given'
                notice.notice_sent_at = timezone.now()
                notice.save()
                messages.warning(request, "Your move-out request has been sent to management.")
                return redirect('tenant_dashboard')
            else:
                messages.error(request, "There was an error with your submission. Please check the date.")

        # 🔄 CANCEL MOVE-OUT NOTICE
        elif 'cancel_move_out' in request.POST:
            if tenant_profile.status == 'notice_given':
                tenant_profile.status = 'active'
                tenant_profile.intended_move_out_date = None
                tenant_profile.move_out_reason = ""
                tenant_profile.notice_sent_at = None
                tenant_profile.save()
                messages.info(request, "Your move-out notice has been successfully cancelled.")
                return redirect('tenant_dashboard')

    # --- 5. FETCH DATA FOR DISPLAY ---
    # We initialize the form here so it appears in the modal for GET requests
    move_out_form = MoveOutRequestForm(instance=tenant_profile)
    
    announcements = Announcement.objects.filter(is_active=True).order_by('-date_posted')[:3]
    my_payments = Payment.objects.filter(tenant=tenant_profile).order_by('-date')[:5]
    my_requests = MaintenanceRequest.objects.filter(tenant=tenant_profile).order_by('-date_reported')[:4]
    
    context = {
        'tenant': tenant_profile,
        'property': tenant_profile.assigned_property,
        'payments': my_payments,
        'requests': my_requests,
        'announcements': announcements,
        'move_out_form': move_out_form, # 👈 Added this to context
    }
    
    return render(request, 'tenants/tenant_dashboard.html', context)
@login_required
def report_issue(request):
    # Security: Ensure only tenants can report issues here
    if request.user.role != 'tenant':
        return redirect('dashboard')
    
    tenant_profile = Tenant.objects.get(user=request.user)

    if request.method == 'POST':
        form = TenantMaintenanceRequestForm(request.POST)
        if form.is_valid():
            # commit=False lets us fill in the tenant hidden from the form
            new_request = form.save(commit=False)
            new_request.tenant = tenant_profile
            new_request.status = 'pending' # Default status for new issues
            new_request.save()
            
            messages.success(request, "Maintenance request submitted successfully!")
            return redirect('tenant_dashboard')
    else:
        form = TenantMaintenanceRequestForm()
    
    return render(request, 'tenants/report_issue.html', {'form': form})

@login_required
def report_payment(request):
    # 1. More reliable way to find the tenant profile
    try:
        # This looks for the Tenant object where the 'user' field matches the current user
        tenant_profile = Tenant.objects.get(user=request.user)
    except Tenant.DoesNotExist:
        messages.error(request, "Error: No tenant profile found for this account.")
        return redirect('login')

    if request.method == 'POST':
        form = TenantPaymentForm(request.POST)
        if form.is_valid():
            # commit=False keeps it in memory so we can add the tenant
            payment = form.save(commit=False)
            
            # 2. Assign the tenant profile we found above
            payment.tenant = tenant_profile
            payment.status = 'pending'
            
            try:
                payment.save()
                messages.success(request, "✅ Payment reported! Management will verify the transaction code shortly.")
                return redirect('tenant_dashboard')
            except IntegrityError as e:
                messages.error(request, f"Database Error: {str(e)}")
    else:
        form = TenantPaymentForm(initial={'method': 'M-Pesa'})
        
    return render(request, 'tenants/report_payment.html', {'form': form})

@login_required
def payment_history(request):
    """Shows a full list of all payments (pending and confirmed) for the logged-in tenant."""
    if request.user.role != 'tenant':
        return redirect('dashboard')
        
    tenant_profile = get_object_or_404(Tenant, user=request.user)
    all_payments = Payment.objects.filter(tenant=tenant_profile).order_by('-date')
    
    return render(request, 'tenants/payment_history.html', {
        'all_payments': all_payments,
        'tenant': tenant_profile
    })

@login_required
def maintenance_history(request):
    """Shows a full archive of all maintenance requests (Resolved and Pending) for the tenant."""
    if request.user.role != 'tenant':
        return redirect('dashboard')

    tenant_profile = get_object_or_404(Tenant, user=request.user)
    all_requests = MaintenanceRequest.objects.filter(tenant=tenant_profile).order_by('-date_reported')
    
    return render(request, 'tenants/maintenance_history.html', {
        'all_requests': all_requests,
        'tenant': tenant_profile
    })


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # ⭐ THE KEY: Flip the flag back to False now that they are secure
            user.must_change_password = False
            user.save()
            
            # Keep the user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            
            # Send them to their specific dashboard
            if user.role == 'tenant':
                return redirect('tenant_dashboard')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {'form': form})

# ==============================================================================
# --- 4. MAINTENANCE & STAFF PORTAL VIEWS ---
# ==============================================================================

@login_required
def maintenance_dashboard(request):
    if request.user.role != 'maintenance':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    # 1. Active Tasks: Jobs specifically assigned to THIS technician that aren't done yet.
    # We filter by status to ensure they don't see "Pending" (unassigned) jobs from other landlords.
    active_tasks = MaintenanceRequest.objects.filter(
        assigned_to=request.user,
        status__in=['assigned', 'in_progress'] # Only show jobs they are currently responsible for
    ).order_by('-priority', '-date_reported')

    # 2. History: The last 5 jobs they personally completed.
    history = MaintenanceRequest.objects.filter(
        assigned_to=request.user, 
        status='completed'
    ).order_by('-date_resolved')[:5]

    return render(request, 'maintenance/technician_dashboard.html', {
        'active_tasks': active_tasks,
        'history': history
    })

@login_required
def update_task(request, pk):
    task = get_object_or_404(MaintenanceRequest, pk=pk, assigned_to=request.user)
    
    if request.method == 'POST':
        form = MaintenanceTaskUpdateForm(request.POST, instance=task)
        if form.is_valid():
            form.save() # Triggers the model's auto-timestamp logic
            messages.success(request, f"Task #{task.id} updated.")
            return redirect('maintenance_dashboard')
    else:
        form = MaintenanceTaskUpdateForm(instance=task)
        
    return render(request, 'maintenance/update_task.html', {'form': form, 'task': task})


# ==============================================================================
# --- 5. ADD DATA VIEWS ---
# ==============================================================================

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
            phone = form.cleaned_data['phone_number']
            first_name = form.cleaned_data['first_name'] # Get this for the message

            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, "User with this email already exists")
                return render(request, 'add_tenant.html', {'form': form})

            # Create User
            user = CustomUser.objects.create(
                username=email, 
                email=email,
                first_name=first_name,
                last_name=form.cleaned_data['last_name'],
                phone_number=phone,
                role='tenant',
                must_change_password=True # Set here during creation
            )

            # Dynamic Password Logic
            clean_password = str(phone).replace(' ', '').replace('+', '').replace('-', '')
            user.set_password(clean_password)
            user.save()

            # Create Tenant Profile
            tenant = form.save(commit=False)
            tenant.user = user
            tenant.balance = tenant.rent_amount 
            tenant.save()
            
            # ⭐ DYNAMIC SUCCESS MESSAGE
            messages.success(request, f'Account created! {first_name} can now log in using their phone number as the password.')
            return redirect('tenants')
    else:
        form = AddTenantFullForm()
        form.fields['assigned_property'].queryset = Property.objects.filter(landlord=request.user)
    
    return render(request, 'add_tenant.html', {'form': form})

def record_payment(request, pk=None):
    # Handle Edit Mode if a primary key is passed
    instance = get_object_or_404(Payment, pk=pk) if pk else None
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=instance)
        if form.is_valid():
            payment = form.save()
            
            # ⭐ THE PRO WAY: Let the model handle the math
            # This ensures the balance is always the sum of all confirmed payments
            payment.tenant.update_balance()
            
            action = "updated" if instance else "recorded"
            messages.success(request, f'Payment {action} for {payment.tenant}')
            return redirect('payments')
    else:
        form = PaymentForm(instance=instance)
        # 🛡️ Security: Only show tenants belonging to THIS landlord
        form.fields['tenant'].queryset = Tenant.objects.filter(
            assigned_property__landlord=request.user
        ).select_related('user') # Performance boost for the __str__ call
        
    return render(request, 'record_payment.html', {
        'form': form,
        'edit_mode': bool(instance)
    })

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


# ==============================================================================
# --- 6. EDIT / DELETE VIEWS (With Ownership Validation) ---
# ==============================================================================

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
        # 1. Capture the old rent before saving the form
        old_rent = tenant.rent_amount
        
        form = AddTenantFullForm(request.POST, instance=tenant)
        if form.is_valid():
            # Update User Details
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.phone_number = form.cleaned_data['phone_number']
            user.save()
            
            # 2. Save tenant with commit=False to check the new rent
            updated_tenant = form.save(commit=False)
            new_rent = updated_tenant.rent_amount
            
            # 3. Adjust balance if the rent amount was changed
            if old_rent != new_rent:
                difference = new_rent - old_rent
                updated_tenant.balance += difference
            
            updated_tenant.save()
            
            messages.success(request, f"Tenant {user.get_full_name()} updated and balance adjusted.")
            return redirect('tenants')
    else:
        initial_data = {
            'first_name': user.first_name, 
            'last_name': user.last_name, 
            'email': user.email, 
            'phone_number': user.phone_number
        }
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

    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            # 1. Save the payment changes (amount, status, etc.)
            form.save()
            
            # 2. ⭐ RECALCULATE EVERYTHING
            # This ignores the old balance and finds the new truth
            tenant.update_balance()
            
            messages.success(request, f"Payment for {tenant.user.get_full_name()} updated and balance synced.")
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
        # 1. Delete the record
        payment.delete()
        
        # 2. ⭐ RECALCULATE EVERYTHING
        # Since the payment is gone, update_balance() will automatically 
        # add that amount back to what the tenant owes.
        tenant.update_balance()
        
        messages.success(request, "Payment deleted. Tenant balance adjusted automatically.")
        return redirect('payments')
        
    return render(request, 'confirm_delete.html', {
        'obj': f"Payment of KES {payment.amount}", 
        'type': 'payment record', 
        'back_url': reverse('payments')
    })

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
        
    # ✅ THE FIX: Added reverse() around 'maintenance'
    return render(request, 'confirm_delete.html', {
        'obj': f"Request #MNT-{maintenance_req.id}", 
        'back_url': reverse('maintenance') 
    })

# ==============================================================================
# --- 7. WORKFLOWS, APPROVALS & ASSIGNMENTS ---
# ==============================================================================

@login_required(login_url='login')
def approve_tenant_signup(request, tenant_id):
    if request.user.role != 'landlord':
        return redirect('tenant_dashboard')

    tenant = get_object_or_404(Tenant, id=tenant_id, assigned_property__landlord=request.user)

    if request.method == 'POST':
        rent_raw = request.POST.get('rent_amount')
        lease_end = request.POST.get('lease_end')

        # ✅ CONVERT TO DECIMAL: Catching empty strings or bad input
        try:
            rent_decimal = Decimal(rent_raw) if rent_raw else Decimal('0.00')
        except (InvalidOperation, TypeError):
            rent_decimal = Decimal('0.00')

        tenant.status = 'active'
        tenant.rent_amount = rent_decimal # Now it's a number, not a string!
        
        if lease_end:
            tenant.lease_end = lease_end
        
        tenant.save()
        
        # Now this method will find numbers on both sides of the minus sign
        tenant.update_balance() 
        
        messages.success(request, f"Account for {tenant.user.get_full_name()} is now active.")
        return redirect('tenants')

    return redirect('tenants')

@login_required(login_url='login')
def reject_tenant_signup(request, tenant_id):
    if request.user.role != 'landlord':
        return redirect('tenant_dashboard')

    # Find the pending tenant linked to this landlord
    tenant = get_object_or_404(Tenant, id=tenant_id, status='pending', assigned_property__landlord=request.user)

    if request.method == 'POST':
        user_to_delete = tenant.user
        tenant.delete() # Remove the profile
        user_to_delete.delete() # Remove the user account
        
        messages.info(request, "Registration request has been rejected and the account removed.")
    
    return redirect('tenants')

@login_required
def approve_move_out(request, tenant_id):
    # Security: Ensure only the landlord who owns the property can approve
    if request.user.role != 'landlord':
        return redirect('dashboard')
        
    tenant = get_object_or_404(
        Tenant, 
        id=tenant_id, 
        assigned_property__landlord=request.user
    )
    
    if request.method == 'POST':
        # Formal Approval: Update status and set the timestamp
        tenant.status = 'approved'
        tenant.landlord_approved_at = timezone.now()
        
        # Sync the lease end with their intended departure
        if tenant.intended_move_out_date:
            tenant.lease_end = tenant.intended_move_out_date
            
        tenant.save()
        
        messages.success(request, f"Move-out notice for {tenant.user.get_full_name()} has been approved.")
        return redirect('tenants') # Go back to the management list

@user_passes_test(lambda u: u.is_staff or getattr(u, 'role', None) == 'landlord')
def approve_payment(request, payment_id):
    # Only allow POST requests for state changes (Security Best Practice)
    if request.method == 'POST':
        payment = get_object_or_404(Payment, id=payment_id)
        
        if payment.status == 'pending':
            tenant = payment.tenant
            
            # 1. Update the Payment Status
            payment.status = 'confirmed'
            payment.save()
            
            # 2. Subtract from Tenant Balance
            # Note: Ensure tenant.balance is a Decimal to match payment.amount
            tenant.balance -= payment.amount
            tenant.save()
            
            messages.success(request, f"✅ Payment {payment.transaction_id} confirmed. KES {payment.amount} subtracted from balance!")
        else:
            messages.warning(request, "This payment has already been processed.")
            
    # Redirect back to the main payments history page
    return redirect('payments')

@login_required
def assign_maintenance(request, pk):
    # 1. Security Check
    if request.user.role != 'landlord':
        messages.error(request, "Access denied.")
        return redirect('dashboard')
        
    task = get_object_or_404(MaintenanceRequest, pk=pk)
    
    if request.method == 'POST':
        # ✅ Pass 'user' so the form can filter the technicians dropdown
        form = MaintenanceAssignmentForm(request.POST, instance=task, user=request.user)
        
        if form.is_valid():
            # Create the object but don't hit the DB yet
            assignment = form.save(commit=False)
            
            # 🔄 AUTOMATION: If a technician is selected, update status
            if assignment.assigned_to:
                assignment.status = 'assigned'
            
            # Save the main record
            assignment.save()
            # Save any many-to-many data if present (good habit!)
            form.save_m2m()
            
            messages.success(request, f"Task #{task.id} assigned to {assignment.assigned_to.get_full_name()}")
            
            # 🚀 REDIRECT: Ensure 'maintenance' is the name in your urls.py
            return redirect('maintenance') 
        else:
            # This is where we caught the 'status required' error earlier
            print(f"Form Errors: {form.errors}") 
            messages.error(request, "Assignment failed. Please check the technician selection.")
    else:
        # GET request: Show the form with the landlord's staff only
        form = MaintenanceAssignmentForm(instance=task, user=request.user)
        
    return render(request, 'maintenance/assign_maintenance.html', {
        'form': form,
        'task': task
    })

@login_required
def manage_staff(request):
    if request.user.role != 'landlord':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    # ✅ FIXED: Show technicians who chose YOU as their landlord but aren't active yet
    pending_staff = CustomUser.objects.filter(
        role='maintenance', 
        is_active=False, 
        employer=request.user # Look for your specific applicants
    )

    # ✅ Show technicians who are active and hired by YOU
    active_staff = CustomUser.objects.filter(
        role='maintenance', 
        is_active=True, 
        employer=request.user
    )

    return render(request, 'manage_staff.html', {
        'pending_staff': pending_staff,
        'active_staff': active_staff
    })

@login_required
def approve_staff(request, pk):
    if request.user.role != 'landlord':
        return redirect('dashboard')
        
    # ✅ FIXED: Ensure you can only approve someone who actually applied to you
    staff = get_object_or_404(
        CustomUser, 
        pk=pk, 
        role='maintenance', 
        is_active=False, 
        employer=request.user
    )
    
    staff.is_active = True
    staff.save()
    
    messages.success(request, f"{staff.get_full_name()} has been added to your maintenance team.")
    return redirect('manage_staff')

@login_required
def reject_staff(request, pk):
    if request.user.role == 'landlord':
        # ✅ FIXED: Only delete if they are YOUR pending applicant
        staff = get_object_or_404(
            CustomUser, 
            pk=pk, 
            role='maintenance', 
            is_active=False, 
            employer=request.user
        )
        staff.delete() 
        messages.warning(request, "Staff application rejected.")
    return redirect('manage_staff')


# ==============================================================================
# --- 8. EXPORTS (Isolated) ---
# ==============================================================================

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


# ==============================================================================
# --- 9. EXTRA UTILITIES & NOTIFICATIONS ---
# ==============================================================================

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