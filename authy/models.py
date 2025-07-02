
from django.db import models

def get_post_model():
    from post.models import Post
    return Post

class UserProfile(models.Model):
    user_bio = models.TextField()

    def get_latest_post(self):
        Post = get_post_model()
        return Post.objects.last()



from django.db import models
from django.contrib.auth.models import User
from post.models import Post

from django.db.models.signals import post_save

from PIL import Image
from django.conf import settings
import os

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'user_{0}/{1}'.format(instance.user.id, filename)

    if os.path.exists(full_path):
    	os.remove(full_path)

    #return profile_pic_name

# Create your models here.
class Profile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
	first_name = models.CharField(max_length=50, null=True, blank=True)
	last_name = models.CharField(max_length=50, null=True, blank=True)
	location = models.CharField(max_length=50, null=True, blank=True)
	url = models.CharField(max_length=80, null=True, blank=True)
	profile_info = models.TextField(max_length=150, null=True, blank=True)
	created = models.DateField(auto_now_add=True)
	favorites = models.ManyToManyField(Post)
	picture = models.ImageField(upload_to=user_directory_path, blank=True, null=True, verbose_name='Picture')

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		SIZE = 250, 250

		if self.picture:
			pic = Image.open(self.picture.path)
			pic.thumbnail(SIZE, Image.LANCZOS)
			pic.save(self.picture.path)

	def __str__(self):
		return self.user.username
		

def create_user_profile(sender, instance, created, **kwargs):
	if created:
		Profile.objects.create(user=instance)

def save_user_profile(sender, instance, **kwargs):
	instance.profile.save()

post_save.connect(create_user_profile, sender=User)
post_save.connect(save_user_profile, sender=User)



#class PostView(models.Model):
    #user = models.ForeignKey(User, on_delete=models.CASCADE)
   # post = models.ForeignKey(Post, on_delete=models.CASCADE)
   # viewed_at = models.DateTimeField(auto_now_add=True)

   # class Meta:
   #     ordering = ['-viewed_at']

   # def __str__(self):
   #     return f"{self.user.username} viewed {self.post.heading}"

   