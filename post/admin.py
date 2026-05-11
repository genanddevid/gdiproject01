from django.contrib import admin
from post.models import Post, Tag, Follow, Stream, SemanticTag

admin.site.register(Post)
admin.site.register(Tag)
admin.site.register(Follow)
admin.site.register(Stream)

@admin.register(SemanticTag)
class SemanticTagAdmin(admin.ModelAdmin):
    list_display = ('post', 'entity', 'category', 'parent_category', 'grandparent_category', 'created_at')
    list_filter = ('category', 'parent_category', 'grandparent_category')
    search_fields = ('entity', 'post__caption')
