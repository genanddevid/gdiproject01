from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        # Try email first
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            # Fall back to username
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return None
        except Exception:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
