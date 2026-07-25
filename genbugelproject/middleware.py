import re
from django.shortcuts import render


class MobileOnlyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.mobile_pattern = re.compile(
            r'Mobile|Android|iPhone|iPad|iPod|BlackBerry|Windows Phone',
            re.IGNORECASE
        )
        self.scraper_pattern = re.compile(
            r'whatsapp|facebookexternalhit|twitterbot|linkedinbot|telegrambot|slackbot',
            re.IGNORECASE
        )
    def __call__(self, request):
        # Always allow admin, static and media regardless of device
        exempt_paths = ('/admin', '/static', '/media')
        if any(request.path.startswith(p) for p in exempt_paths):
            return self.get_response(request)
        # Logged-in staff can always access desktop
        if request.user.is_authenticated and request.user.is_staff:
            return self.get_response(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        # Let social media scrapers through so PostDetails can serve OG tags
        if self.scraper_pattern.search(user_agent):
            return self.get_response(request)
        is_mobile = bool(self.mobile_pattern.search(user_agent))
        if not is_mobile:
            return render(request, 'desktop_notice.html')
        return self.get_response(request)