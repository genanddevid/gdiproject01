"""
URL configuration for genbugelproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

#from .views import frontpage
from authy import views as authy_views 
from post.views import NarrativeBuilder, interests_view
from authy.views import UserProfile, follow, discover_view

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.index, name='index'),  # 👈 ADD THIS FIRST
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('narrative_builder/', NarrativeBuilder, name='narrativebuilder'),
    path('discover/', discover_view, name='discover'),
    path('interests/', interests_view, name='interests'),
    
    path('comment/', include('comment.urls')),

    path('collections/', authy_views.all_collections_view, name='all_collections'),
    path('collections/saved/', authy_views.collections_view, name='collections_saved'),
    path('collections/history/', authy_views.collections_history_view, name='collections_history'),
    path('collections/liked_comments/', authy_views.collections_liked_comments_view, name='collections_liked_comments'),
    path('collections/liked_posts/', authy_views.collections_liked_posts_view, name='collections_liked_posts'),
    path('collections/commented_comments/', authy_views.collections_commented_comments_view, name='collections_commented_comments'),
    path('collections/commented_posts/', authy_views.collections_commented_posts_view, name='collections_commented_posts'),
    path('collections/notifications/', authy_views.collections_notifications_view, name='collections_notifications'),
    
    path('', include('post.urls')),  # e.g. /post/
    path('', include('authy.urls')),  # e.g. /login/, /signup/
    
    path('<username>/', UserProfile, name='profile'),
    path('<username>/saved', UserProfile, name='profilefavorites'),
    path('<username>/follow/<option>', follow, name='follow'), 
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)






#from django.contrib import admin
#from django.urls import path, include
#from django.conf import settings
#from django.conf.urls.static import static


#urlpatterns = [
    #path('admin/', admin.site.urls),
   # path('user/', include('authy.urls')),
#] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
   

