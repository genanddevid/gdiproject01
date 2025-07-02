from django.db import models
from django.contrib.auth.models import User
import uuid
from django.db.models.signals import post_save
from django.utils.text import slugify
from django.urls import reverse
from django.utils import timezone
from django.conf import settings


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'user_{0}/{1}'.format(instance.user.id, filename)

# Tag model
class Tag(models.Model):
    title = models.CharField(max_length=75, verbose_name='Tag')
    slug = models.SlugField(null=False, unique=True)

    class Meta:
        verbose_name_plural = 'Tags'

    #def get_absolute_url(self):
        #return reverse('tags', args=[self.slug])
        
    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        return super().save(*args, **kwargs)

# Post model
class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    picture = models.ImageField(upload_to=user_directory_path, verbose_name='Picture', null=False, default='defaults/default.jpg')
   # picture = models.ImageField(upload_to='posts/', blank=True, null=True)
    caption = models.TextField(max_length=1500, verbose_name='Caption', default='Default caption text')
    posted = models.DateTimeField(auto_now_add=True)  # This will automatically set the time when a post is created. one of the two should be deleted
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True) # This will automatically set the time when a post is created. one of the two should be deleted
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='posts', null=True, blank=True)
    #tags = models.ManyToManyField(Tag, related_name='tags')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    likes = models.IntegerField(default=0)
    link1 = models.URLField(blank=False, null=True)
    link2 = models.URLField(blank=True, null=True)


    def __str__(self):
        return self.caption[:50]  # Returns first 50 characters of the caption


    def get_absolute_url(self):
        return reverse('postdetails', args=[str(self.id)])

# Follow model
class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follower')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')

# Stream model
class Stream(models.Model):
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stream_following')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    date = models.DateTimeField()

# Signal handler for adding posts to the stream
def add_post(sender, instance, *args, **kwargs):
    post = instance
    user = post.user
    followers = Follow.objects.filter(following=user)
    for follower in followers:
        stream = Stream(
            post=post,
            user=follower.follower,
            date=post.posted,
            following=user
        )
        stream.save()

class Likes(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_like')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_likes')

# Connect the post_save signal to the add_post function
post_save.connect(add_post, sender=Post)


class SavedItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='saved_posts')
    saved_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} saved {self.post.id}"


class PostView(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey('Post', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')  # Optional: avoid duplicates

    def __str__(self):
        return f"{self.user} viewed {self.post}"


class ApprovedTagAuthor(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approved_tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='approved_authors')

    class Meta:
        unique_together = ('author', 'tag')  # Ensure one entry per combination

    def __str__(self):
        return f"{self.author.username} + {self.tag.title}"









