import re
from django.shortcuts import render


class MobileOnlyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.mobile_pattern = re.compile(
            r'Mobile|Android|iPhone|iPad|iPod|BlackBerry|Windows Phone',
            re.IGNORECASE
        )

    def __call__(self, request):
        # Always allow admin, static and media regardless of device
        exempt_paths = ('/admin/', '/static/', '/media/')
        if any(request.path.startswith(p) for p in exempt_paths):
            return self.get_response(request)

        user_agent = request.META.get('HTTP_USER_AGENT', '')
        is_mobile = bool(self.mobile_pattern.search(user_agent))

        if not is_mobile:
            return render(request, 'desktop_notice.html')

        return self.get_response(request)