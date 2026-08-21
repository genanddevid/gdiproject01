
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
from django.contrib import messages

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
import os

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
	follow_status = (
        request.user.is_authenticated and
        Follow.objects.filter(following=user, follower=request.user).exists()
    )

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
    from django.utils import timezone
    
    if not request.user.is_authenticated:
        posts = Post.objects.all().select_related(
            'user__profile'
        ).order_by('-likes', '-posted')
        return render(request, 'discover.html', {
            'posts': posts,
            'active_page': 'discover',
        })
    
    user = request.user
    
    # ONE query — get user interests
    from datetime import timedelta
    now = timezone.now()
    confirmed_interests = UserInterest.objects.filter(
        user=user,
        click_count__gte=2,
        last_clicked__gte=now - timedelta(days=14)
    )
    interest_entities = set(ui.entity for ui in confirmed_interests)
    interest_categories = set(ui.category for ui in confirmed_interests)
    interest_parent_categories = set(ui.parent_category for ui in confirmed_interests if ui.parent_category)
    interest_grandparent_categories = set(ui.grandparent_category for ui in confirmed_interests if ui.grandparent_category)
    # ONE query — followed writers
    followed_user_ids = set(
        Follow.objects.filter(follower=user).values_list('following_id', flat=True)
    )
    
    # THREE queries — build exclusion sets
    entity_excluded_post_ids = set(
        SemanticTag.objects.filter(entity__in=interest_entities)
        .values_list('post_id', flat=True)
    ) if interest_entities else set()
    
    category_excluded_post_ids = set(
        SemanticTag.objects.filter(category__in=interest_categories)
        .values_list('post_id', flat=True)
    ) if interest_categories else set()
    
    parent_excluded_post_ids = set(
        SemanticTag.objects.filter(parent_category__in=interest_parent_categories)
        .values_list('post_id', flat=True)
    ) if interest_parent_categories else set()
    
    # ONE query — followed posts
    followed_post_ids = set(
        Post.objects.filter(user_id__in=followed_user_ids)
        .values_list('id', flat=True)
    ) if followed_user_ids else set()
    
    all_excluded_ids = (
        entity_excluded_post_ids | 
        category_excluded_post_ids | 
        parent_excluded_post_ids | 
        followed_post_ids
    )
    
    # Self-adjusting quality floor — median likes across all posts, capped low
    from django.db.models import Avg
    all_likes = list(Post.objects.values_list('likes', flat=True))
    if all_likes:
        sorted_likes = sorted(all_likes)
        mid = len(sorted_likes) // 2
        median_likes = sorted_likes[mid]
    else:
        median_likes = 0
    quality_floor = max(0, median_likes // 2)  # half the median, so it doesn't over-filter

    # ONE query — get discover posts with select_related
    discover_posts = Post.objects.exclude(
        id__in=all_excluded_ids
    ).exclude(user=user).filter(likes__gte=quality_floor).select_related('user__profile')

    
    # ONE query — pre-fetch all semantic tags for discover posts
    discover_post_ids = [p.id for p in discover_posts]
    all_tags = SemanticTag.objects.filter(
        post_id__in=discover_post_ids
    ).values('post_id', 'grandparent_category')
    
    post_grandparent_map = {}
    for tag in all_tags:
        pid = tag['post_id']
        if pid not in post_grandparent_map:
            post_grandparent_map[pid] = set()
        if tag['grandparent_category']:
            post_grandparent_map[pid].add(tag['grandparent_category'])
    
    # Score in Python — zero extra queries
    scored_posts = []
    for post in discover_posts:
        score = post.likes
        
        post_grandparent_cats = post_grandparent_map.get(post.id, set())
        is_opposite = (
            post_grandparent_cats and
            not post_grandparent_cats & interest_grandparent_categories
        )
        
        if is_opposite:
            score += 3
        
        scored_posts.append((score, post))
    
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



def Signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')

            beta_mode = os.environ.get('BETA_MODE', 'True') == 'True'
            matching_cohort = None
            matching_member = None

            if beta_mode:
                from authy.models import Cohort, CohortMemberEmail
                matching_cohort = Cohort.objects.filter(partner_email__iexact=email, is_active=True).first()
                matching_member = CohortMemberEmail.objects.filter(email__iexact=email, is_active=True).first()

                if not matching_cohort and not matching_member:
                    form.add_error(None, "Baytruyen is currently invite-only for our beta pilot. If you believe you should have access, please contact your program lead.")
                    return render(request, 'signup.html', {'form': form})

            user = User.objects.create_user(username=username, email=email, password=password)

            if matching_cohort:
                matching_cohort.partner_user = user
                matching_cohort.save()
            elif matching_member:
                matching_member.member_user = user
                matching_member.save()

            login(request, user, backend='genbugelproject.backends.EmailOrUsernameBackend')
            return redirect('profile', username=username)
    else:
        form = SignupForm()
    context = {
        'form':form,
    }
    return render(request, 'signup.html', context)

def get_member_stats(member):
    """Compute beta tracking metrics for a single CohortMemberEmail"""
    from authy.models import LoginEvent, ReviewWritingLog, ReadTimeLog, WritewordLookupLog
    from post.models import Post
    from comment.models import Comment
    from django.db.models import Sum
    from datetime import timedelta

    if not member.member_user:
        return {
            'email': member.email, 'joined': False,
            'logins': 0, 'stories': 0, 'words': 0, 'comments': 0,
            'read_minutes': 0, 'ai_reviews': 0, 'likes': 0, 'w1_err': 0, 'w2_err': 0,
            'lookups': 0,
        }

    user = member.member_user
    join_date = user.date_joined

    logins = LoginEvent.objects.filter(user=user).count()

    posts = Post.objects.filter(user=user)
    stories = posts.count()
    words = sum(len(p.content.split()) for p in posts)

    comments = Comment.objects.filter(user=user).count()

    read_seconds = ReadTimeLog.objects.filter(user=user).aggregate(total=Sum('seconds'))['total'] or 0
    read_minutes = read_seconds // 60

    ai_reviews = ReviewWritingLog.objects.filter(user=user).count()

    week1_end = join_date + timedelta(days=7)
    week2_end = join_date + timedelta(days=14)

    w1_err = ReviewWritingLog.objects.filter(
        user=user, created_at__gte=join_date, created_at__lt=week1_end
    ).aggregate(total=Sum('issue_count'))['total'] or 0

    w2_err = ReviewWritingLog.objects.filter(
        user=user, created_at__gte=week1_end, created_at__lt=week2_end
    ).aggregate(total=Sum('issue_count'))['total'] or 0

    lookups = WritewordLookupLog.objects.filter(user=user).count()

    from post.models import Likes
    likes_received = Likes.objects.filter(post__user=user).count()

    return {
        'email': member.email, 'joined': True,
        'logins': logins, 'stories': stories, 'words': words, 'comments': comments,
        'read_minutes': read_minutes, 'ai_reviews': ai_reviews, 'likes': likes_received,
        'w1_err': w1_err, 'w2_err': w2_err,
        'lookups': lookups,
    }


FRIENDLY_METRIC_LABELS = {
    'logins': 'Logins', 'stories': 'Stories', 'words': 'Words', 'comments': 'Comments',
    'read_minutes': 'Read Time', 'ai_reviews': 'AI Reviews', 'lookups': 'Lookups', 'likes': 'Likes',
}

def get_cohort_milestones(member_stats):
    cohort_size = 10
    totals = {
        'logins': sum(s['logins'] for s in member_stats),
        'stories': sum(s['stories'] for s in member_stats),
        'words': sum(s['words'] for s in member_stats),
        'comments': sum(s['comments'] for s in member_stats),
        'read_minutes': sum(s['read_minutes'] for s in member_stats),
        'ai_reviews': sum(s['ai_reviews'] for s in member_stats),
        'lookups': sum(s['lookups'] for s in member_stats),
        'likes': sum(s['likes'] for s in member_stats),
        'w1_err': sum(s['w1_err'] for s in member_stats),
        'w2_err': sum(s['w2_err'] for s in member_stats),
    }
    targets_per_student = {
        'logins': 14, 'stories': 14, 'words': 3500, 'comments': 28,
        'read_minutes': 140, 'ai_reviews': 14, 'lookups': 28, 'likes': 28,
    }

    milestones = {}
    lowest_pct = 100
    bottleneck_key = None

    for key, target in targets_per_student.items():
        cohort_target = target * cohort_size
        trigger = cohort_target * 0.8
        raw_pct = round((totals[key] / cohort_target) * 100) if cohort_target else 0
        milestones[key] = {
            'total': totals[key],
            'cohort_target': cohort_target,
            'trigger': int(trigger),
            'met': totals[key] >= trigger,
            'progress_pct': raw_pct,
        }
        gating_pct = min(raw_pct, 100)
        if gating_pct < lowest_pct:
            lowest_pct = gating_pct
            bottleneck_key = key

    all_met = lowest_pct >= 80
    bottleneck_label = FRIENDLY_METRIC_LABELS.get(bottleneck_key, bottleneck_key)

    # Informational only — does NOT gate the download
    w1_err, w2_err = totals['w1_err'], totals['w2_err']
    reduction_met = w1_err > 0 and w2_err <= (w1_err * 0.72)
    milestones['error_reduction'] = {'w1': w1_err, 'w2': w2_err, 'met': reduction_met}

    return milestones, all_met, lowest_pct, bottleneck_label



@login_required
def download_cohort_report(request):
    from authy.models import Cohort, ReviewWritingLog, WritewordLookupLog
    from post.models import PostView
    import requests
    from django.db.models import Count
    from io import BytesIO
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch

    is_admin = request.user.is_staff or request.user.is_superuser

    if is_admin:
        cohort_id = request.GET.get('cohort_id')
        cohort = Cohort.objects.filter(id=cohort_id, is_active=True).first() if cohort_id else None
        if not cohort:
            return HttpResponse('Cohort not found.', status=404)
    else:
        cohort = Cohort.objects.filter(partner_user=request.user, is_active=True).first()
        if not cohort:
            return HttpResponse('Not authorized', status=403)

    members = cohort.members.filter(is_active=True).order_by('email')
    member_stats = [get_member_stats(m) for m in members]
    milestones, all_milestones_met, lowest_pct, bottleneck_label = get_cohort_milestones(member_stats)

    if not all_milestones_met and not is_admin:
        messages.error(request, "The report unlocks once every pilot milestone has been reached.")
        return redirect('ca_dashboard')


    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.6*inch, bottomMargin=0.6*inch, leftMargin=0.5*inch, rightMargin=0.5*inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('ReportTitle', parent=styles['Title'], fontSize=16, spaceAfter=4)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], spaceBefore=14, spaceAfter=8)
    small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=9, textColor=colors.grey)
    body_style = styles['Normal']
    story = []

    # Page 1 — Cover + Engagement Matrix
    story.append(Paragraph("Baytruyen Pilot Cohort Performance Report", title_style))
    active_testers = sum(1 for s in member_stats if s['joined'])
    story.append(Paragraph(f"Partner: {request.user.username} &nbsp;|&nbsp; Institution: {cohort.institution_name or '—'}", body_style))
    story.append(Paragraph(f"Cohort Size: {members.count()} Students &nbsp;|&nbsp; Active Testers: {active_testers}/{members.count()}", body_style))
    story.append(Spacer(1, 16))
    story.append(Paragraph("Cohort Quantitative Engagement Matrix", section_style))

    table_data = [['Email', 'Logins', 'Stories', 'Words', 'Comments', 'Read (min)', 'AI Rev.', 'Likes', 'W1 Err', 'W2 Err', 'Lookups']]
    for s in member_stats:
        table_data.append([s['email'], s['logins'], s['stories'], s['words'], s['comments'], s['read_minutes'], s['ai_reviews'], s['likes'], s['w1_err'], s['w2_err'], s['lookups']])
    totals_row = ['TOTAL']
    for key in ['logins', 'stories', 'words', 'comments', 'read_minutes', 'ai_reviews', 'likes', 'w1_err', 'w2_err', 'lookups']:
        totals_row.append(sum(s[key] for s in member_stats))
    table_data.append(totals_row)

    engagement_table = Table(table_data, repeatRows=1, colWidths=[2.15*inch, 0.7*inch, 0.7*inch, 0.8*inch, 0.8*inch, 0.9*inch, 0.7*inch, 0.65*inch, 0.65*inch, 0.65*inch, 0.75*inch])
    engagement_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(engagement_table)
    story.append(PageBreak())

    # Page 2 — Qualitative Writing & Pedagogical Growth
    story.append(Paragraph("Qualitative Writing & Pedagogical Growth", section_style))

    member_user_ids = [m.member_user_id for m in members if m.member_user_id]
    all_logs = ReviewWritingLog.objects.filter(user_id__in=member_user_ids)

    w1_total = sum(s['w1_err'] for s in member_stats)
    w2_total = sum(s['w2_err'] for s in member_stats)
    total_interventions = sum(log.issue_count for log in all_logs)

    story.append(Paragraph("1. Cohort Syntax Evolution Metrics", styles['Heading3']))
    story.append(Paragraph(f"Total AI Review Interventions Logged: {total_interventions}", body_style))
    story.append(Paragraph(f"Week 1 Interventions: {w1_total} &nbsp;|&nbsp; Week 2 Interventions: {w2_total}", body_style))
    if w1_total > 0:
        reduction = round(((w1_total - w2_total) / w1_total) * 100, 1)
        story.append(Paragraph(f"<b>Correction Reduction Rate:</b> {reduction}% drop between Week 1 and Week 2.", body_style))
    story.append(Spacer(1, 14))

    story.append(Paragraph("2. Error Category Breakdown", styles['Heading3']))
    category_counts = (
        all_logs.values('category').annotate(total=Count('id')).order_by('-total')
    )
    category_sum = sum(c['total'] for c in category_counts)
    if category_sum > 0:
        cat_data = [['Category', 'Reviews', 'Share']]
        for c in category_counts:
            pct = round((c['total'] / category_sum) * 100)
            cat_data.append([c['category'].capitalize(), c['total'], f"{pct}%"])
        cat_table = Table(cat_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(cat_table)
    else:
        story.append(Paragraph("No reviews recorded yet.", body_style))
    story.append(Spacer(1, 14))

    story.append(Paragraph("3. Representative Before &amp; After Snippets", styles['Heading3']))
    snippet_count = 0
    for m in members:
        if not m.member_user or snippet_count >= 6:
            continue
        log = all_logs.filter(
            user=m.member_user, issues_detail__isnull=False
        ).exclude(issues_detail=[]).order_by('-created_at').first()

        if log and log.issues_detail:
            issue = log.issues_detail[0]
            original = (issue.get('original', '') or '')[:150]
            suggestion = (issue.get('suggestion', '') or '')[:150]
            story.append(Paragraph(f"<b>{m.email}</b> &nbsp;<font color='#888'>({log.category})</font>", body_style))
            story.append(Paragraph(f"<i>Original:</i> \u201c{original}\u201d", body_style))
            story.append(Paragraph(f"<i>Correction:</i> \u201c{suggestion}\u201d", body_style))
            story.append(Spacer(1, 10))
            snippet_count += 1
    story.append(PageBreak())

    # Page 3 — Vocabulary Acquisition & Reading Analytics
    story.append(Paragraph("Vocabulary Acquisition & Reading Analytics (Writeword)", section_style))

    story.append(Paragraph("1. Reading Engagement Overview", styles['Heading3']))
    total_stories_read = PostView.objects.filter(user_id__in=member_user_ids).count()
    total_read_minutes = sum(s['read_minutes'] for s in member_stats)
    total_lookups = sum(s['lookups'] for s in member_stats)
    story.append(Paragraph(f"Total Peer Narratives Read: {total_stories_read}", body_style))
    story.append(Paragraph(f"Total Reading Time Logged: {total_read_minutes} minutes", body_style))
    story.append(Paragraph(f"Total Writeword Lookups: {total_lookups}", body_style))
    story.append(Spacer(1, 14))

    story.append(Paragraph("2. Top Words Looked Up During Reading", styles['Heading3']))
    top_words = (
        WritewordLookupLog.objects.filter(user_id__in=member_user_ids)
        .values('word').annotate(count=Count('word')).order_by('-count')[:10]
    )
    if top_words:
        word_data = [['Word', 'Times Looked Up', 'Arabic Translation']]
        for w in top_words:
            translation = '—'
            try:
                resp = requests.get(
                    'https://api.mymemory.translated.net/get',
                    params={'q': w['word'], 'langpair': 'en|ar'},
                    timeout=5
                )
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get('responseStatus') == 200:
                        translation = result['responseData'].get('translatedText', '—')
            except Exception:
                pass
            word_data.append([w['word'], w['count'], translation])

        word_table = Table(word_data, colWidths=[2.2*inch, 1.6*inch, 2.2*inch])
        word_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(word_table)
    else:
        story.append(Paragraph("No lookups recorded yet.", body_style))

    story.append(Spacer(1, 14))
    story.append(Paragraph("<b>Word Adoption Tracking:</b> not yet available — coming in a future update.", small_style))

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    filename = f"baytruyen_cohort_report_{cohort.partner_email.split('@')[0]}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response




@login_required
def ca_dashboard(request):
    from authy.models import Cohort, CohortMemberEmail, Feedback
    import json

    is_admin = request.user.is_staff or request.user.is_superuser

    if is_admin:
        cohort_id = request.GET.get('cohort_id')
        all_cohorts = Cohort.objects.filter(is_active=True).order_by('partner_email')
        if cohort_id:
            cohort = all_cohorts.filter(id=cohort_id).first()
        else:
            cohort = all_cohorts.first()
        if not cohort:
            return HttpResponse('No active cohorts exist yet.', status=404)
    else:
        cohort = Cohort.objects.filter(partner_user=request.user, is_active=True).first()
        all_cohorts = None
        if not cohort:
            return HttpResponse('Not authorized', status=403)

    if request.method == 'POST':
        if is_admin:
            return HttpResponse('Admins manage cohorts through Django admin, not this view.', status=403)

        action = request.POST.get('action')

        if action == 'add':
            email = request.POST.get('email', '').strip().lower()
            if email:
                already_partner = Cohort.objects.filter(partner_email__iexact=email, is_active=True).exists()
                existing_member = CohortMemberEmail.objects.filter(email__iexact=email).first()

                if already_partner:
                    messages.error(request, f"{email} is already a Partner.")
                elif existing_member and existing_member.is_active:
                    messages.error(request, f"{email} is already an active member of a cohort.")
                elif cohort.members.filter(is_active=True).count() >= 10:
                    messages.error(request, "This cohort already has 10 members.")
                elif existing_member:
                    existing_member.cohort = cohort
                    existing_member.is_active = True
                    existing_member.save()
                    if existing_member.member_user:
                        existing_member.member_user.is_active = True
                        existing_member.member_user.save()
                    messages.success(request, f"Reinstated {email}.")
                else:
                    CohortMemberEmail.objects.create(cohort=cohort, email=email)
                    messages.success(request, f"Added {email}.")

        elif action == 'remove':
            member_id = request.POST.get('member_id')
            member = CohortMemberEmail.objects.filter(id=member_id, cohort=cohort).first()
            if member:
                member.is_active = False
                member.save()
                if member.member_user:
                    member.member_user.is_active = False
                    member.member_user.save()
                messages.success(request, f"Removed {member.email}.")

        return redirect('ca_dashboard')

    members = cohort.members.filter(is_active=True).order_by('email')

    member_email_by_user_id = {m.member_user_id: m.email for m in members if m.member_user_id}
    cohort_feedback = Feedback.objects.filter(
        user_id__in=member_email_by_user_id.keys()
    ).select_related('user')
    for fb in cohort_feedback:
        fb.cohort_email = member_email_by_user_id.get(fb.user_id, '')

    member_stats = [get_member_stats(m) for m in members]
    milestones, all_milestones_met, lowest_pct, bottleneck_label = get_cohort_milestones(member_stats)
    totals = {
        'logins': sum(s['logins'] for s in member_stats),
        'stories': sum(s['stories'] for s in member_stats),
        'words': sum(s['words'] for s in member_stats),
        'comments': sum(s['comments'] for s in member_stats),
        'read_minutes': sum(s['read_minutes'] for s in member_stats),
        'ai_reviews': sum(s['ai_reviews'] for s in member_stats),
        'likes': sum(s['likes'] for s in member_stats),
        'w1_err': sum(s['w1_err'] for s in member_stats),
        'w2_err': sum(s['w2_err'] for s in member_stats),
        'lookups': sum(s['lookups'] for s in member_stats),
    }

   return render(request, 'ca_dashboard.html', {
        'cohort': cohort,
        'members': members,
        'cohort_feedback': cohort_feedback,
        'member_stats': member_stats,
        'totals': totals,
        'milestones': milestones,
        'all_milestones_met': all_milestones_met,
        'lowest_pct': lowest_pct,
        'bottleneck_label': bottleneck_label,
        'all_cohorts': all_cohorts,
        'is_admin': is_admin,
    })


@login_required
def feedback_view(request):
    from authy.models import Feedback

    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        if body:
            Feedback.objects.create(user=request.user, body=body)
            messages.success(request, "Thank you — your feedback has been sent.")
        return redirect('feedback')

    my_feedback = Feedback.objects.filter(user=request.user)

    return render(request, 'feedback.html', {
        'my_feedback': my_feedback,
    })


