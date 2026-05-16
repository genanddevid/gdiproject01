from django.contrib import admin
from post.models import Post, Tag, Follow, Stream, SemanticTag, UserInterest

admin.site.register(Post)
admin.site.register(Tag)
admin.site.register(Follow)
admin.site.register(Stream)

@admin.register(SemanticTag)
class SemanticTagAdmin(admin.ModelAdmin):
    list_display = ('post', 'entity', 'category', 'parent_category', 'grandparent_category', 'created_at')
    list_filter = ('category', 'parent_category')
    search_fields = ('entity', 'post__caption')

@admin.register(UserInterest)
class UserInterestAdmin(admin.ModelAdmin):
    list_display = ('user', 'entity', 'category', 'parent_category', 'click_count', 'last_clicked')
    list_filter = ('category', 'parent_category')
    search_fields = ('user__username', 'entity')




    
    
