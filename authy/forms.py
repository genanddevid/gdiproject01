from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from authy.models import Profile

def ForbiddenUsers(value):
	forbidden_users = ['admin', 'css', 'js', 'authenticate', 'login', 'logout', 'administrator', 'root',
	'email', 'user', 'join', 'sql', 'static', 'python', 'delete']
	if value.lower() in forbidden_users:
		raise ValidationError('Invalid name for user, this is a reserverd word.')

def InvalidUser(value):
	if '@' in value or '+' in value or '-' in value:
		raise ValidationError('This is an Invalid user, Do not user these chars: @ , - , + ')

def UniqueEmail(value):
	if User.objects.filter(email__iexact=value).exists():
		raise ValidationError('User with this email already exists.')

def UniqueUser(value):
	if User.objects.filter(username__iexact=value).exists():
		raise ValidationError('User with this username already exists.')

class SignupForm(forms.ModelForm):
	username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username'}), max_length=30, required=True,)
	email = forms.CharField(widget=forms.EmailInput(attrs={'placeholder': 'Email'}), max_length=100, required=True,)
	password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
	confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}), required=True, label="Confirm your password.")

	class Meta:
		model = User
		fields = ('username', 'email', 'password')

	def __init__(self, *args, **kwargs):
		super(SignupForm, self).__init__(*args, **kwargs)
		self.fields['username'].validators.append(ForbiddenUsers)
		self.fields['username'].validators.append(InvalidUser)
		self.fields['username'].validators.append(UniqueUser)
		self.fields['email'].validators.append(UniqueEmail)

	def clean(self):
		super(SignupForm, self).clean()
		password = self.cleaned_data.get('password')
		confirm_password = self.cleaned_data.get('confirm_password')

		if password != confirm_password:
			self._errors['password'] = self.error_class(['Passwords do not match. Try again'])
		return self.cleaned_data

class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input is-medium'}), label="Old password")
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input is-medium'}), label="New password")
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input is-medium'}), label="Confirm new password")

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data['old_password']
        if not self.user.check_password(old_password):
            raise ValidationError('Your old password is incorrect.')
        return old_password

    def clean(self):
        cleaned = super().clean()
        new_password = cleaned.get('new_password')
        confirm_password = cleaned.get('confirm_password')
        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned

class EditProfileForm(forms.ModelForm):
    picture = forms.ImageField(required=False)

    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'input is-medium'}),
        max_length=50,
        required=False
    )

    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'input is-medium'}),
        max_length=50,
        required=False
    )

    location = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'input is-medium'}),
        max_length=25,
        required=False
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'input is-medium'}),
        max_length=100,
        required=True
    )

    profile_info = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'input is-medium'}),
        max_length=500,
        required=False
    )

    class Meta:
        model = Profile
        fields = (
            'picture',
            'first_name',
            'last_name',
            'location',
            'email',
            'profile_info',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.initial['email'] = self.instance.user.email

    def clean_email(self):
        email = self.cleaned_data['email'].strip()

        if User.objects.filter(email__iexact=email).exclude(
            pk=self.instance.user_id
        ).exists():
            raise ValidationError('User with this email already exists.')

        return email

    def save(self, commit=True):
        profile = super().save(commit=commit)

        if commit:
            user = profile.user
            user.email = self.cleaned_data['email']
            user.save(update_fields=['email'])

        return profile

from django import forms
from django.contrib.auth.forms import AuthenticationForm

class CustomLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(CustomLoginForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Username',
            'class': 'input'  # Bulma input class
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Password',
            'class': 'input'
        })
