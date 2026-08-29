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
        self.post_url_pattern = re.compile(
            r'^/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/?$',
            re.IGNORECASE
        )

    def __call__(self, request):
        exempt_paths = ('/admin', '/static', '/media')
        if any(request.path.startswith(p) for p in exempt_paths):
            return self.get_response(request)

        # Individual article URLs: let PostDetails decide scraper vs human.
        # No User-Agent guessing here — this is what makes link previews
        # work regardless of what any given bot claims to be.
        if self.post_url_pattern.match(request.path):
            return self.get_response(request)

        if request.user.is_authenticated and request.user.is_staff:
            return self.get_response(request)

        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if self.scraper_pattern.search(user_agent):
            return self.get_response(request)

        is_mobile = bool(self.mobile_pattern.search(user_agent))
        if not is_mobile:
            return render(request, 'desktop_notice.html')

        return self.get_response(request)
