from django.db import models
from django.contrib.auth.models import User
from post.models import Post
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


def get_post_model():
    from post.models import Post
    return Post


class UserProfile(models.Model):
    user_bio = models.TextField()

    def get_latest_post(self):
        Post = get_post_model()
        return Post.objects.last()


def user_directory_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'user_{0}/{1}'.format(instance.user.id, filename)


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    first_name = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    last_name = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    location = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    url = models.CharField(
        max_length=80,
        null=True,
        blank=True
    )

    profile_info = models.TextField(
        max_length=150,
        null=True,
        blank=True
    )

    created = models.DateField(auto_now_add=True)

    favorites = models.ManyToManyField(Post)

    picture = models.ImageField(
        upload_to=user_directory_path,
        blank=True,
        null=True,
        verbose_name='Picture'
    )

    notifications_last_seen = models.DateTimeField(
        null=True,
        blank=True
    )

    pinned_post = models.ForeignKey(
        'post.Post',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pinned_by'
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # SIZE = 250, 250
        # if self.picture:
        #     pic = Image.open(self.picture.path)
        #     pic.thumbnail(SIZE, Image.LANCZOS)
        #     pic.save(self.picture.path)

    def __str__(self):
        return self.user.username


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


post_save.connect(create_user_profile, sender=User)
post_save.connect(save_user_profile, sender=User)


class Cohort(models.Model):
    """A Partner's cohort for the beta pilot"""

    partner_email = models.EmailField(unique=True)

    partner_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='partner_cohort'
    )

    institution_name = models.CharField(
        max_length=200,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.partner_email} ({self.institution_name or 'no institution set'})"

    def save(self, *args, **kwargs):
        if self.pk:
            previous = Cohort.objects.filter(pk=self.pk).first()

            if (
                previous
                and previous.is_active
                and not self.is_active
                and self.partner_user
            ):
                self.partner_user.is_active = False
                self.partner_user.save()

        super().save(*args, **kwargs)


class CohortMemberEmail(models.Model):
    """A Member email allowed into a specific Partner's cohort during beta"""

    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.CASCADE,
        related_name='members'
    )

    email = models.EmailField(unique=True)

    member_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cohort_membership'
    )

    is_active = models.BooleanField(default=True)

    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} → {self.cohort.partner_email}"


class Feedback(models.Model):
    """Beta pilot feedback from a Partner or Member"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='beta_feedback'
    )

    body = models.TextField(max_length=2000)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.body[:50]}"


class LoginEvent(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_events'
    )

    timestamp = models.DateTimeField(auto_now_add=True)


@receiver(user_logged_in)
def log_login_event(sender, request, user, **kwargs):
    LoginEvent.objects.create(user=user)


class ReviewWritingLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='review_writing_logs'
    )

    category = models.CharField(max_length=20)

    issue_count = models.IntegerField(default=0)

    issues_detail = models.JSONField(
        default=list,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)


class ReadTimeLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='read_time_logs'
    )

    post = models.ForeignKey(
        'post.Post',
        on_delete=models.CASCADE
    )

    seconds = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)


class WritewordLookupLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='writeword_lookups'
    )

    word = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)