
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
from comment.models import Comment, CommentLike
from django.utils import timezone
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


@login_required
def collections_liked_comments_view(request):
    liked_comments = Comment.objects.filter(likes__user=request.user).select_related('user', 'user__profile', 'post').order_by('-date')
    context = {
        'comments': liked_comments,
        'active_page': 'all_collections',
    }
    return render(request, 'collections_liked_comments.html', context)


@login_required
def collections_posted_comments_view(request):
    posted_comments = Comment.objects.filter(user=request.user, parent__isnull=True).select_related('user', 'user__profile', 'post').order_by('-date')
    context = {
        'comments': posted_comments,
        'active_page': 'all_collections',
    }
    return render(request, 'collections_posted_comments.html', context)


@login_required
def collections_posted_replies_view(request):
    posted_replies = Comment.objects.filter(user=request.user, parent__isnull=False).select_related('user', 'user__profile', 'post').order_by('-date')
    context = {
        'comments': posted_replies,
        'active_page': 'all_collections',
    }
    return render(request, 'collections_posted_replies.html', context)





@login_required
def collections_liked_posts_view(request):
    liked_posts = Post.objects.filter(post_likes__user=request.user).distinct().order_by('-posted')
    context = {
        'posts': liked_posts,
        'active_page': 'all_collections',
    }
    return render(request, 'collections_liked_posts.html', context)

@login_required
def collections_notifications_view(request):
    me = request.user
    last_seen = me.profile.notifications_last_seen

    notifications = []

    # 1. Likes on MY posts (someone liked a post I wrote)
    post_likes = Likes.objects.filter(post__user=me).exclude(user=me).select_related('user', 'user__profile', 'post')
    for like in post_likes:
        notifications.append({
            'type': 'post_like',
            'actor': like.user,
            'post': like.post,
            'comment': None,
            'timestamp': like.liked_at,
            'text': 'liked your post',
        })

    # 2. Comments on MY posts (someone commented on a post I wrote) - top-level only
    post_comments = Comment.objects.filter(post__user=me, parent__isnull=True).exclude(user=me).select_related('user', 'user__profile', 'post')
    for comment in post_comments:
        notifications.append({
            'type': 'post_comment',
            'actor': comment.user,
            'post': comment.post,
            'comment': comment,
            'timestamp': comment.date,
            'text': 'commented on your post',
        })

    # 3. Replies to MY comments (someone replied to a comment I wrote)
    my_comment_ids = Comment.objects.filter(user=me).values_list('id', flat=True)
    replies = Comment.objects.filter(parent__in=my_comment_ids).exclude(user=me).select_related('user', 'user__profile', 'post')
    for reply in replies:
        notifications.append({
            'type': 'reply',
            'actor': reply.user,
            'post': reply.post,
            'comment': reply,
            'timestamp': reply.date,
            'text': 'replied to your comment',
        })

    # 4. Likes on MY comments (someone liked a comment I wrote)
    comment_likes = CommentLike.objects.filter(comment__user=me).exclude(user=me).select_related('user', 'user__profile', 'comment', 'comment__post')
    for clike in comment_likes:
        notifications.append({
            'type': 'comment_like',
            'actor': clike.user,
            'post': clike.comment.post,
            'comment': clike.comment,
            'timestamp': clike.liked_at,
            'text': 'liked your comment',
        })

    # Filter out any with no timestamp (old post-likes from before the migration)
    notifications = [n for n in notifications if n['timestamp'] is not None]

    # Sort newest first
    notifications.sort(key=lambda n: n['timestamp'], reverse=True)

    # Mark each as read/unread
    for n in notifications:
        if last_seen is None:
            n['unread'] = True
        else:
            n['unread'] = n['timestamp'] > last_seen

    # Update last_seen to now (so next visit, these are "read")
    me.profile.notifications_last_seen = timezone.now()
    me.profile.save()

    context = {
        'notifications': notifications,
        'active_page': 'all_collections',
    }
    return render(request, 'collections_notifications.html', context)





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
        'active_page': 'all_collections',
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
    from post.models import SemanticTag, UserInterest
    
    if not request.user.is_authenticated:
        # Guest users see all posts ordered by likes
        posts = Post.objects.all().order_by('-likes', '-posted')
        return render(request, 'discover.html', {
            'posts': posts,
            'active_page': 'discover',
        })
    
    user = request.user
    
    # Get user's interests
    user_interests = UserInterest.objects.filter(user=user)
    interest_entities = set(ui.entity for ui in user_interests)
    interest_categories = set(ui.category for ui in user_interests)
    interest_parent_categories = set(ui.parent_category for ui in user_interests if ui.parent_category)
    interest_grandparent_categories = set(ui.grandparent_category for ui in user_interests if ui.grandparent_category)
    
    # Get followed writers
    followed_user_ids = set(
        Follow.objects.filter(follower=user).values_list('following_id', flat=True)
    )
    
    # Build exclusion sets from semantic tags
    # Exclude entity matches
    entity_excluded_post_ids = set(
        SemanticTag.objects.filter(entity__in=interest_entities)
        .values_list('post_id', flat=True)
    )
    
    # Exclude category matches
    category_excluded_post_ids = set(
        SemanticTag.objects.filter(category__in=interest_categories)
        .values_list('post_id', flat=True)
    )
    
    # Exclude parent category matches
    parent_excluded_post_ids = set(
        SemanticTag.objects.filter(parent_category__in=interest_parent_categories)
        .values_list('post_id', flat=True)
    )
    
    # All excluded post IDs
    all_excluded_ids = entity_excluded_post_ids | category_excluded_post_ids | parent_excluded_post_ids
    
    # Also exclude posts from followed writers
    followed_post_ids = set(
        Post.objects.filter(user_id__in=followed_user_ids)
        .values_list('id', flat=True)
    )
    all_excluded_ids = all_excluded_ids | followed_post_ids
    
    # Get all remaining posts for Discover (exclude own posts)
    discover_posts = Post.objects.exclude(id__in=all_excluded_ids).exclude(user=user)
    
    # Score each post
    scored_posts = []
    for post in discover_posts:
        score = post.likes  # Base score is likes
        
        # Check if post is a true opposite
        # (grandparent categories have zero overlap with user interests)
        post_grandparent_cats = set(
            SemanticTag.objects.filter(post=post)
            .values_list('grandparent_category', flat=True)
        )
        
        is_opposite = (
            post_grandparent_cats and
            not post_grandparent_cats & interest_grandparent_categories
        )
        
        if is_opposite:
            score += 3  # Boost opposites slightly
        
        scored_posts.append((score, post))
    
    # Sort by score descending
    scored_posts.sort(key=lambda x: x[0], reverse=True)
    posts = [post for score, post in scored_posts]
    
    return render(request, 'discover.html', {
        'posts': posts,
        'active_page': 'discover',
    })







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
    return render(request, 'collections_history.html', {'viewed_posts': viewed_posts, 'active_page': 'all_collections'})
