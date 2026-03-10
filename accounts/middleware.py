from django.shortcuts import redirect
from django.urls import reverse

class PasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Check if user is logged in
        if request.user.is_authenticated:
            # 2. List of URLs they ARE allowed to visit (to avoid infinite loops)
            allowed_urls = [
                reverse('change_password'),
                reverse('logout'),
            ]
            
            # 3. If they MUST change password and are trying to go elsewhere...
            if request.user.must_change_password and request.path not in allowed_urls:
                return redirect('change_password')

        return self.get_response(request)