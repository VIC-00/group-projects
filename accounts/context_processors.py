from .models import Tenant, CustomUser

def global_tenants(request):
    """
    Provides global data to all templates. 
    Matches the name in settings.py: 'accounts.context_processors.global_tenants'
    """
    if request.user.is_authenticated and request.user.role == 'landlord':
        return {
            # 1. Isolation: Only show tenants belonging to THIS landlord for the Mass Message dropdown
            'global_tenants': Tenant.objects.filter(
                assigned_property__landlord=request.user
            ).select_related('user', 'assigned_property'),
            
            # 2. Notifications: The red badge count for staff applications waiting for THIS landlord
            'pending_staff_count': CustomUser.objects.filter(
                role='maintenance', 
                is_active=False, 
                employer=request.user
            ).count(),
        }
    
    # Return empty if not a landlord or not logged in
    return {}