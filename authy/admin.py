from django.contrib import admin
from authy.models import Profile
# Register your models here.

admin.site.register(Profile)


from authy.models import Cohort, CohortMemberEmail, Feedback

@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ('partner_email', 'institution_name', 'partner_user', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('partner_email', 'institution_name')

@admin.register(CohortMemberEmail)
class CohortMemberEmailAdmin(admin.ModelAdmin):
    list_display = ('email', 'cohort', 'member_user', 'is_active', 'added_at')
    list_filter = ('is_active', 'cohort')
    search_fields = ('email',)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_email', 'body_preview', 'created_at')
    search_fields = ('user__username', 'user__email', 'body')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def body_preview(self, obj):
        return obj.body[:80]
    body_preview.short_description = 'Feedback'
