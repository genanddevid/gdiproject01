from django.contrib import admin
from post.models import Post, Tag, Follow, Stream, SemanticTag, UserInterest, ApprovedWriterEntity, BannerAd, PostView

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

@admin.register(ApprovedWriterEntity)
class ApprovedWriterEntityAdmin(admin.ModelAdmin):
    list_display = ('writer', 'entity', 'approved_at')
    search_fields = ('writer__username', 'entity')

@admin.register(BannerAd)
class BannerAdAdmin(admin.ModelAdmin):
    list_display = ('advertiser', 'description', 'status', 'impressions', 'created_at')
    list_filter = ('status',)
    search_fields = ('advertiser__username', 'description', 'entities')

@admin.register(PostView)
class PostViewAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'timestamp')
    list_filter = ('user',)
    search_fields = ('user__username', 'post__caption')
    ordering = ('-timestamp',)








    
    
