from django.urls import path
from . import views
from .views import submit_reply

urlpatterns = [
   path('<int:comment_id>/like/', views.like_comment, name='like-comment'),
   path('<int:comment_id>/reply/', submit_reply, name='submit_reply'),
]

