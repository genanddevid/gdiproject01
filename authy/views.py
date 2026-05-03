
from django.shortcuts import render

def home(request):
    return render(request, 'index.html')

def login_view(request):
    return render(request, 'login.html')

def signup_view(request):
    return render(request, 'signup.html')



















from django.shortcuts import render, redirect, get_object_or_404
from authy.forms import SignupForm, ChangePasswordForm, EditProfileForm
from django.contrib.auth.models import User

from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash, login

from authy.models import Profile
from post.models import Post, Follow, Likes, Stream
from django.db import transaction
from django.template import loader
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse

from django.core.paginator import Paginator

from django.urls import resolve
import random


from django.http import JsonResponse

from django.template.loader import render_to_string

#from .models import PostView

@login_required
def collections_history(request):
    postviews = PostView.objects.filter(user=request.user).order_by('-timestamp')
    posts = [view.post for view in postviews]

    return render(request, 'collections_history.html', {'posts': posts})


# Create your views here.
def UserProfile(request, username):
	user = get_object_or_404(User, username=username)
	profile = Profile.objects.get(user=user)
	url_name = resolve(request.path).url_name
	
	#if url_name == 'profile':
	posts = Post.objects.filter(user=user).order_by('-posted')
	#else:
	#posts = profile.favorites.all()

	#Profile info stats
	posts_count = Post.objects.filter(user=user).count()
	following_count = Follow.objects.filter(follower=user).count()
	followers_count = Follow.objects.filter(following=user).count()
	likes_count = Likes.objects.filter(user=user).count()
	#comment_count = Comment.objects.filter(user=user).count()


	#follow status
	follow_status = Follow.objects.filter(following=user, follower=request.user).exists()

	#Pagination
	paginator = Paginator(posts, 62)
	page_number = request.GET.get('page')
	posts_paginator = paginator.get_page(page_number)

	template = loader.get_template('profile.html')

	context = {
		'posts': posts_paginator,
		'profile':profile,
		'url_name':url_name,
		'following_count':following_count,
		'followers_count':followers_count,
		'posts_count':posts_count,
		'likes_count': likes_count,
		#'comment_count': comment_count,
		'follow_status':follow_status,
		'active_page': 'profile',
		'is_own_profile': request.user.is_authenticated and request.user.username == username,
	}

	return HttpResponse(template.render(context, request))









#def all_collections_view(request):
    #return render(request, 'collections.html')

#@login_required
#def all_collections_view(request):
 #   # Add any data logic here, if needed
   # return render(request, 'all_collections.html')

def all_collections_view(request):
    # Add any data logic here, if needed
    context = {
        'active_page': 'all_collections', # Set the active page
    }
    return render(request, 'collections.html', context)




def collections_history_view(request):
    # You can pass context with history data if needed
    return render(request, 'collections_history.html')


def collections_liked_comments_view(request):
    # You can pass context with history data if needed
    return render(request, 'collections_liked_comments.html')

@login_required
def collections_liked_posts_view(request):
    liked_posts = Post.objects.filter(post_likes__user=request.user).distinct().order_by('-posted')
    context = {
        'posts': liked_posts
    }
    return render(request, 'collections_liked_posts.html', context)

def collections_commented_comments_view(request):
    # You can pass context with history data if needed
    return render(request, 'collections_commented_comments.html')



def collections_commented_posts_view(request):
    commented_posts = Post.objects.filter(comments__user=request.user).distinct().order_by('-posted')
    context = {
        'posts': commented_posts
    }
    return render(request, 'collections_commented_posts.html', context)


def collections_notifications_view(request):
    # You can pass context with history data if needed
    return render(request, 'collections_notifications.html')




@login_required
def collections_view(request):
	user = request.user
	profile = Profile.objects.get(user=user)
	url_name = resolve(request.path).url_name
	
	#if url_name == 'profile':
	#posts = Post.objects.filter(user=user).order_by('-posted')

	#else:
	posts = profile.favorites.all().order_by('-posted')


	#Profile info box
	#posts_count = Post.objects.filter(user=user).count()
	#following_count = Follow.objects.filter(follower=user).count()
	#followers_count = Follow.objects.filter(following=user).count()

	#follow status
	#follow_status = Follow.objects.filter(following=user, follower=request.user).exists()

	#Pagination
	paginator = Paginator(posts, 8)
	page_number = request.GET.get('page')
	posts_paginator = paginator.get_page(page_number)

	template = loader.get_template('profile.html')

	context = {
		'posts': posts_paginator,
		'profile':profile,
		#'following_count':following_count,
		#'followers_count':followers_count,
		#'posts_count':posts_count,
		#'follow_status':follow_status,
		'url_name':url_name,
	}

	return render(request, 'collections_saved.html', context)



@login_required
def collections_history(request):
    postviews = PostView.objects.filter(user=request.user).order_by('-timestamp')
    posts = [view.post for view in postviews]

    return render(request, 'collections_history.html', {'posts': posts})





	

def UserProfileFavorites(request, username):
	user = get_object_or_404(User, username=username)
	profile = Profile.objects.get(user=user)
	
	posts = profile.favorites.all()

	#Profile info box
	#posts_count = Post.objects.filter(user=user).count()
	#following_count = Follow.objects.filter(follower=user).count()
	#followers_count = Follow.objects.filter(following=user).count()

	#Pagination
	paginator = Paginator(posts, 8)
	page_number = request.GET.get('page')
	posts_paginator = paginator.get_page(page_number)

	template = loader.get_template('profile_favorite.html')

	context = {
		'posts': posts_paginator,
		'profile':profile,
		#'following_count':following_count,
		#'followers_count':followers_count,
		#'posts_count':posts_count,
	}

	return HttpResponse(template.render(context, request))


def Signup(request):
	if request.method == 'POST':
		form = SignupForm(request.POST)
		if form.is_valid():
			username = form.cleaned_data.get('username')
			email = form.cleaned_data.get('email')
			password = form.cleaned_data.get('password')
			user = User.objects.create_user(username=username, email=email, password=password)
			login(request, user, backend='genbugelproject.backends.EmailOrUsernameBackend')
			return redirect('profile', username=username)
	else:
		form = SignupForm()
	context = {
		'form':form,
	}

	return render(request, 'signup.html', context)



@login_required
def PasswordChange(request):
	user = request.user
	if request.method == 'POST':
		form = ChangePasswordForm(request.POST)
		if form.is_valid():
			new_password = form.cleaned_data.get('new_password')
			user.set_password(new_password)
			user.save()
			update_session_auth_hash(request, user)
			return redirect('change_password_done')
	else:
		form = ChangePasswordForm(instance=user)

	context = {
		'form':form,
	}

	return render(request, 'change_password.html', context)

def PasswordChangeDone(request):
	return render(request, 'change_password_done.html')






@login_required
def EditProfile(request):
    user = request.user
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        # If no profile exists, create one linked to the user
        profile = Profile.objects.create(user=user)

    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect(reverse('profile', kwargs={'username': request.user.username}))
    else:
        form = EditProfileForm(instance=profile)

    context = {
        'form': form
    }

    return render(request, 'edit_profile.html', context)







@login_required
def follow(request, username, option):
    user = request.user
    following = get_object_or_404(User, username=username)

    try:
        f, created = Follow.objects.get_or_create(follower=request.user, following=following)

        if int(option) == 0:
            f.delete()
            Stream.objects.filter(following=following, user=request.user).delete()
        else:
            posts = Post.objects.filter(user=following)[:10]

            with transaction.atomic():
                for post in posts:
                    stream = Stream(post=post, user=request.user, date=post.posted, following=following)
                    stream.save()

        return HttpResponseRedirect(reverse('profile', args=[username]))
    except User.DoesNotExist:
        return HttpResponseRedirect(reverse('profile', args=[username]))




#def discover_view(request):
   # posts = Post.objects.all().order_by('-created_at')  # newest first
   # return render(request, 'discover.html', {'posts': posts})





def discover_view(request):
    posts = Post.objects.all().order_by('-created_at')  # newest first
    context = {
        'posts': posts,
        'active_page': 'discover', # Add active_page here
    }
    return render(request, 'discover.html', context)






#def discover_view(request):
    #if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
       # offset = int(request.GET.get('offset', 0))
       # limit = 10  # Adjust chunk size as needed
        #posts = list(Post.objects.all()[offset:offset+limit])

        # Create blocks of random layouts
        #layouts = ['big', 'small_scroll', 'thin']
        #blocks = []

        #while posts:
         #   layout = random.choice(layouts)
         #   count = 1 if layout == 'big' else (5 if layout == 'small_scroll' else random.randint(1, 3))
          #  block_posts = posts[:count]
          #  posts = posts[count:]
          #  blocks.append({'layout': layout, 'posts': block_posts})

       # html = render_to_string('partials/post_blocks.html', {'blocks': blocks})
       # return JsonResponse({'html': html})
    
    #return render(request, 'discover.html')  # initial page load





def load_more_posts(request):
    page = request.GET.get('page', 1)

    # Replace this with your real post queryset
    posts = Post.objects.all()  

    # Simulate random block layouts
    layouts = ['big', 'small_scroll', 'thin']
    post_blocks = []

    chunk_size = 6  # Number of posts per scroll
    paginator = Paginator(posts, chunk_size)
    current_page = paginator.get_page(page)

    for post in current_page.object_list:
        layout = random.choice(layouts)
        post_blocks.append({'layout': layout, 'posts': [post]})

    return render(request, 'partials/post_blocks.html', {'blocks': post_blocks})


from django.shortcuts import render
from post.models import PostView

@login_required
def collections_history_view(request):
    user = request.user
    viewed_posts = PostView.objects.filter(user=user).order_by('-timestamp')
    return render(request, 'collections_history.html', {'viewed_posts': viewed_posts})
