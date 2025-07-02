
from django.urls import path
from django.contrib.auth import views as authViews 
from . import views
from .forms import CustomLoginForm
from django.contrib.auth.views import LoginView
from authy.views import UserProfile, Signup, PasswordChange, PasswordChangeDone, EditProfile, discover_view

urlpatterns = [
    path('profile/edit', EditProfile, name='edit-profile'),
    path('signup/', Signup, name='signup'),
    path('login/', LoginView.as_view(
        template_name='login.html',
        authentication_form=CustomLoginForm
    ), name='login'),
    path('logout/', authViews.LogoutView.as_view(), {'next_page' : 'index'}, name='logout'),
    path('changepassword/', PasswordChange, name='change_password'),
    path('changepassword/done', PasswordChangeDone, name='change_password_done'),
    path('passwordreset/', authViews.PasswordResetView.as_view(), name='password_reset'),
    path('passwordreset/done', authViews.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('passwordreset/<uidb64>/<token>/', authViews.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('passwordreset/complete/', authViews.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('discover/', discover_view, name='discover'),
    path('load-more-posts/', views.load_more_posts, name='load_more_posts'),

   
]










