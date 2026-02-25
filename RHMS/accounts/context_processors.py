from .models import Tenant

def global_tenants(request):
    if request.user.is_authenticated:
        return {'global_tenants': Tenant.objects.select_related('user', 'assigned_property').all()}
    return {}