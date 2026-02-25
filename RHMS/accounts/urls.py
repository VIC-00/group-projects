from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    
    # Properties
    path('properties/', views.properties_view, name='properties'),
    path('properties/add/', views.add_property, name='add_property'),
    path('properties/<int:pk>/', views.property_detail, name='property_detail'),
    path('properties/edit/<int:pk>/', views.edit_property, name='edit_property'),
    path('properties/delete/<int:pk>/', views.delete_property, name='delete_property'),
    path('properties/export/', views.export_properties_csv, name='export_properties_csv'),
    path('properties/import/', views.import_properties, name='import_properties'),
    
    # Tenants
    path('tenants/', views.tenants_view, name='tenants'),
    path('tenants/add/', views.add_tenant, name='add_tenant'),
    path('tenants/edit/<int:pk>/', views.edit_tenant, name='edit_tenant'),
    path('tenants/delete/<int:pk>/', views.delete_tenant, name='delete_tenant'),
    path('export/tenants/', views.export_tenants_csv, name='export_tenants_csv'),
    
    # Payments
    path('payments/', views.payments_view, name='payments'),
    path('payments/record/', views.record_payment, name='record_payment'),
    path('payments/edit/<int:pk>/', views.edit_payment, name='edit_payment'),
    path('payments/delete/<int:pk>/', views.delete_payment, name='delete_payment'),
    path('payments/export/', views.export_payments_csv, name='export_payments_csv'),    
    path('payments/invoice/<int:pk>/', views.generate_invoice, name='generate_invoice'),
    
    # Maintenance
    path('maintenance/', views.maintenance_view, name='maintenance'),
    path('maintenance/add/', views.add_maintenance, name='add_maintenance'),
    path('maintenance/edit/<int:pk>/', views.edit_maintenance, name='edit_maintenance'),
    path('maintenance/delete/<int:pk>/', views.delete_maintenance, name='delete_maintenance'),
    path('maintenance/export/', views.export_maintenance_csv, name='export_maintenance_csv'),
    
    # Reports & Settings
    path('reports/', views.reports_view, name='reports'),
    path('reports/export/revenue/', views.export_revenue_csv, name='export_revenue_csv'),
    path('reports/export/arrears/', views.export_arrears_csv, name='export_arrears_csv'),
    path('settings/', views.settings_view, name='settings'),
    path('send-mass-message/', views.send_mass_message, name='send_mass_message'),
]