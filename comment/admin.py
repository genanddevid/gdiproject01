from django.contrib import admin

# Register your models here.
from .models import Comment, CommentLike

admin.site.register(Comment)
admin.site.register(CommentLike)
