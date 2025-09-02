


from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.template import loader
from django.contrib.auth.decorators import login_required

#Models:
from post.models import Post, Stream, Tag, Likes
from authy.models import Profile  # Only import SavedItem from authy if it's defined there
from comment.models import Comment
from .models import PostView

#Forms:
from post.forms import NarrativeBuilderForm
from comment.forms import CommentForm


from post.models import SavedItem


from django.db.models import Q



import re
import math

def split_into_sentences(text):
    # Avoid splitting on common abbreviations
    abbreviations = r"(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|e\.g|i\.e|etc)\."
    text = re.sub(abbreviations, lambda x: x.group(0).replace('.', '<DOT>'), text)

    # Split on ., !, or ? followed by a space and a capital letter
    sentence_endings = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
    sentences = sentence_endings.split(text)

    # Restore dots in abbreviations
    sentences = [s.replace('<DOT>', '.') for s in sentences]

    return [s.strip() for s in sentences if s.strip()]



def divide_content(sentences, parts=2):
    # Split the list of sentences into `parts` chunks as balanced as possible
    total = len(sentences)
    avg = total / float(parts)
    chunks = []
    last = 0.0

    while last < total:
        next_split = last + avg
        chunks.append(sentences[int(last):int(next_split)])
        last = next_split

    return [' '.join(chunk) for chunk in chunks]






@login_required
def index(request):
    return render(request, 'index.html')
    


@login_required
def interests_view(request):
    user = request.user
    posts = Stream.objects. filter(user=user)

    group_ids = []

    for post in posts:
        group_ids.append(post.post_id)

    post_items = Post.objects.filter(id__in=group_ids).all().order_by('-posted')

    template = loader.get_template('interests.html')

    context = {
        'post_items': post_items,
        'active_page': 'interests',
    }

    return HttpResponse(template.render(context, request))


@login_required
def PostDetails(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    user = request.user

    # Log the post view
    if request.user.is_authenticated:
        PostView.objects.get_or_create(user=request.user, post=post)

    liked = Likes.objects.filter(user=user, post=post).exists()
    form = CommentForm()
    favorited = False
    comments = Comment.objects.filter(post=post).order_by('date')

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.user = user
            comment.save()
            return HttpResponseRedirect(reverse('postdetails', args=[post_id]))

    if request.user.is_authenticated:
        profile = Profile.objects.get(user=request.user)
        if profile.favorites.filter(id=post_id).exists():
            favorited = True

    total_comment_count = Comment.objects.filter(post=post).count()

    # ✅ Recommendation logic — keep this *inside* the view function
    all_other_posts = Post.objects.exclude(id=post.id).exclude(user=request.user).order_by('id')

    left_recommendations = []
    right_recommendations = []

    for i, p in enumerate(all_other_posts):
        if len(left_recommendations) >= 3 and len(right_recommendations) >= 3:
            break  # Stop if both sides are full
        if i % 2 == 0 and len(left_recommendations) < 3:
            left_recommendations.append(p)
        elif i % 2 == 1 and len(right_recommendations) < 3:
            right_recommendations.append(p)

    # Content splitting logic
    sentences = split_into_sentences(post.content)

    if post.link1 and post.link2:
        split_parts = divide_content(sentences, parts=3)
    elif post.link1:
        split_parts = divide_content(sentences, parts=2)
    else:
        split_parts = [post.content]  # Only one part if no links

    content1 = split_parts[0] if len(split_parts) > 0 else ''
    content2 = split_parts[1] if len(split_parts) > 1 else ''
    content3 = split_parts[2] if len(split_parts) > 2 else ''

    is_approved = ApprovedTagAuthor.objects.filter(
    author=post.user, tag=post.tag
    ).exists()

    
    context = {
        'post': post,
        'liked': liked,
        'favorited': favorited,
        'form': form,
        'comments': comments,
        'total_comment_count': total_comment_count,
        'left_recommendations': left_recommendations,
        'right_recommendations': right_recommendations,
        'content1': content1,
        'content2': content2,
        'content3': content3,
        'is_approved': is_approved,  # 👈 add this
    }

    

    return render(request, 'post_detail.html', context)

from django.shortcuts import render, get_object_or_404
from .models import Post

def post_modal(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    user = request.user

    if request.user.is_authenticated:
        PostView.objects.get_or_create(user=request.user, post=post)

    liked = Likes.objects.filter(user=user, post=post).exists()
    form = CommentForm()
    favorited = False
    comments = Comment.objects.filter(post=post).order_by('date')

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.user = user
            comment.save()
            form = CommentForm()  # reset form
            comments = Comment.objects.filter(post=post).order_by('date')  

    if request.user.is_authenticated:
        profile = Profile.objects.get(user=request.user)
        if profile.favorites.filter(id=post_id).exists():
            favorited = True

    total_comment_count = Comment.objects.filter(post=post).count()

    all_other_posts = Post.objects.exclude(id=post.id).exclude(user=request.user).order_by('id')
    left_recommendations = []
    right_recommendations = []

    for i, p in enumerate(all_other_posts):
        if len(left_recommendations) >= 3 and len(right_recommendations) >= 3:
            break
        if i % 2 == 0 and len(left_recommendations) < 3:
            left_recommendations.append(p)
        elif i % 2 == 1 and len(right_recommendations) < 3:
            right_recommendations.append(p)

    sentences = split_into_sentences(post.content)

    if post.link1 and post.link2:
        split_parts = divide_content(sentences, parts=3)
    elif post.link1:
        split_parts = divide_content(sentences, parts=2)
    else:
        split_parts = [post.content]

    content1 = split_parts[0] if len(split_parts) > 0 else ''
    content2 = split_parts[1] if len(split_parts) > 1 else ''
    content3 = split_parts[2] if len(split_parts) > 2 else ''

    is_approved = ApprovedTagAuthor.objects.filter(
        author=post.user, tag=post.tag
    ).exists()

    context = {
        'post': post,
        'liked': liked,
        'favorited': favorited,
        'form': form,
        'comments': comments,
        'total_comment_count': total_comment_count,
        'left_recommendations': left_recommendations,
        'right_recommendations': right_recommendations,
        'content1': content1,
        'content2': content2,
        'content3': content3,
        'is_approved': is_approved,
    }

    return render(request, "post_detail_modal.html", context)







from django.shortcuts import render, redirect, reverse
from django.contrib.auth.decorators import login_required
from post.forms import NarrativeBuilderForm

@login_required
def NarrativeBuilder(request):
    if request.method == "POST":
        form = NarrativeBuilderForm(request.POST, request.FILES)
        if form.is_valid():
            # The form's save() handles tag assignment now
            post_instance = form.save(commit=False)
            post_instance.user = request.user
            post_instance.save()

            # Clear preview data after actual save
            request.session.pop('preview_data', None)
            return redirect(reverse('profile', kwargs={'username': request.user.username}))
    else:
        # Restore from session if available
        preview_data = request.session.get('preview_data')
        if preview_data:
            form = NarrativeBuilderForm(initial={
                'caption': preview_data.get('caption'),
                'content': preview_data.get('content'),
                'tag': preview_data.get('tag'),
                'link1': preview_data.get('link1'),
                'link2': preview_data.get('link2'),
            })

        else:
            form = NarrativeBuilderForm()

    context = {
        'form': form,
        'active_page': 'narrativebuilder',
    }

    return render(request, 'narrativebuilder.html', context)


from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid


@login_required
def preview_narrative(request, post_id=None):
    instance = None
    if post_id:
        instance = get_object_or_404(Post, id=post_id, user=request.user)

    if request.method == "POST":
        form = NarrativeBuilderForm(request.POST, request.FILES, instance=instance)

        if form.is_valid():
            request.session['preview_data'] = {
                'caption': form.cleaned_data.get('caption'),
                'content': form.cleaned_data.get('content'),
                'tag': form.cleaned_data.get('tag').id if form.cleaned_data.get('tag') else None,
                'link1': form.cleaned_data.get('link1'),
                'link2': form.cleaned_data.get('link2'),
                'post_id': str(post_id) if post_id else None,
            }

            temp_image_url = None
            if 'picture' in request.FILES:
                picture_file = request.FILES['picture']
                unique_filename = f"temp/{uuid.uuid4()}_{picture_file.name}"
                saved_path = default_storage.save(unique_filename, ContentFile(picture_file.read()))
                temp_image_url = default_storage.url(saved_path)

                request.session['preview_data']['picture'] = saved_path  

            post = form.save(commit=False)
            post.user = request.user

            return render(request, 'narrative_preview.html', {
                'post': post,
                'image_url': temp_image_url,
                'edit_mode': bool(post_id),  # useful for "Back to edit"
                'post_id': post_id,
            })

    # fallback: if something failed
    if post_id:
        return redirect('edit_post', post_id=post_id)
    return redirect('narrativebuilder')











from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def like(request, post_id):
    user = request.user
    post = get_object_or_404(Post, id=post_id)

    liked = Likes.objects.filter(user=user, post=post).exists()

    if liked:
        Likes.objects.filter(user=user, post=post).delete()
        post.likes -= 1
        liked = False
    else:
        Likes.objects.create(user=user, post=post)
        post.likes += 1
        liked = True

    post.save()

    return JsonResponse({'likes': post.likes, 'liked': liked})



    

@login_required
def favorite(request, post_id):
    user = request.user
    post = Post.objects.get(id=post_id)
    profile = Profile.objects.get(user=user)

    if profile.favorites.filter(id=post_id).exists():
        profile.favorites.remove(post)

    else:
        profile.favorites.add(post)

    return HttpResponse(status=204)  # No redirect, just success




#@login_required
#def favorite(request, post_id):
    #user = request.user
   # post = get_object_or_404(Post, id=post_id)

   # saved_item, created = SavedItem.objects.get_or_create(user=user, post=post)

    #if not created:
       # saved_item.delete()  # Unsave if already saved

   # return HttpResponseRedirect(reverse('postdetails', args=[post_id]))





@login_required
def collections_view(request):
    return render(request, 'collections_saved.html')

@login_required
def collections_liked_posts_view(request):
    return render(request, 'collections_liked_posts.html')

@login_required
def your_saves(request):
    saved_items = SavedItem.objects.filter(user=request.user).select_related('post')
    return render(request, 'collections_saved.html', {'saved_items': saved_items})


@login_required
def all_collections_view(request):
    # Add any data logic here, if needed
    return render(request, 'all_collections.html')

    








@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, user=request.user)  # Ensures only post owner can delete
    if request.method == "POST":
        post.delete()
        return redirect('profile', username=request.user.username)
    return render(request, 'delete_post_confirm.html', {'post': post})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, user=request.user)
    
    if request.method == 'POST':
        form = NarrativeBuilderForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            request.session.pop('preview_data', None) 
            return redirect('profile', username=request.user.username )  # or wherever you want to redirect
    else:
        preview_data = request.session.get('preview_data')
        if preview_data and str(post.id) == preview_data.get('post_id'):
            form = NarrativeBuilderForm(initial={
                'caption': preview_data.get('caption'),
                'content': preview_data.get('content'),
                'tag': preview_data.get('tag'),
                'link1': preview_data.get('link1'),
                'link2': preview_data.get('link2'),
            }, instance=post)
            del request.session['preview_data']  # clear session after resto
        else:
            # Build comma-separated string of tag titles for initial display
            tags_str = post.tag.title if post.tag else ''
            form = NarrativeBuilderForm(instance=post, initial={'tags': tags_str})
    
    return render(request, 'narrativebuilder.html', {
        'form': form, 
        'edit_mode': True,
        'post': post,
        })



@login_required
def finalize_edit(request, post_id):
    preview_data = request.session.get('preview_data')
    post = get_object_or_404(Post, id=post_id, user=request.user)

    if request.method == 'POST' and preview_data:
        # Pop out the image path from session
        picture_path = preview_data.pop('picture', None)

        form = NarrativeBuilderForm(data=preview_data, instance=post, allow_missing_picture=True)

        if form.is_valid():
            updated_post = form.save(commit=False)

            # ✅ Save updated image if provided
            if picture_path:
                with default_storage.open(picture_path, 'rb') as f:
                    updated_post.picture.save(picture_path.split('/')[-1], File(f))

            updated_post.save()
            request.session.pop('preview_data', None)
            return redirect('profile', username=request.user.username)

    return redirect('edit_post', post_id=post_id)


from django.core.files import File

@login_required
def finalize_new_post(request):
    preview_data = request.session.get('preview_data')

    if request.method == 'POST' and preview_data:
        

        # Remove 'picture' from data because it's not an upload, it's a path
        picture_path = preview_data.pop('picture', None)

        # Create the form without the picture
       
        form = NarrativeBuilderForm(data=preview_data, allow_missing_picture=True)


        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user

            # ✅ Attach picture manually if it exists
            if picture_path:
                with default_storage.open(picture_path, 'rb') as f:
                    post.picture.save(picture_path.split('/')[-1], File(f))

            post.save()

            # Clean up
            request.session.pop('preview_data', None)
            return redirect('profile', username=request.user.username)
        

    return redirect('narrativebuilder')






from post.models import PostView

@login_required
def view_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    PostView.objects.get_or_create(user=request.user, post=post)
    return redirect('postdetails', post_id=post_id)




#def collections_history(request):
    #user = request.user
    #print(f"Collections history requested by: {user}")  # Debug line
   # viewed_posts = PostView.objects.filter(user=user).order_by('-timestamp')  # newest first
    
   # return render(request, 'post/collections_history.html', {'viewed_posts': viewed_posts})


    
from .models import Post, ApprovedTagAuthor
from django.db.models import Q  # Make sure this is at the top



@login_required
def index(request):
    # Get all (user, tag) combinations approved by the editor
    approved_combos = ApprovedTagAuthor.objects.all()

    if approved_combos.exists():
        # Only include posts that match approved (user, tag) combos
        query = Q()
        for combo in approved_combos:
            query |= Q(user=combo.author, tag=combo.tag)

        posts = Post.objects.filter(query).order_by('-posted')
    else:
        # If no approvals yet, Frontpage should be empty
        posts = Post.objects.none()

    posts = list(posts)  # Convert queryset to list for slicing

    layout_blocks = []
    idx = 0
    total = len(posts)

    # First block layout (1 large, 1 scroll, 2 large, 23 medium)
    if total >= 1:
        layout_blocks.append({'type': 'large', 'posts': posts[idx:idx+1]})
        idx += 1
    if total >= idx + 4:
        layout_blocks.append({'type': 'scroll', 'posts': posts[idx:idx+4]})
        idx += 4
    if total >= idx + 2:
        layout_blocks.append({'type': 'large', 'posts': posts[idx:idx+2]})
        idx += 2
    if total >= idx + 23:
        layout_blocks.append({'type': 'medium', 'posts': posts[idx:idx+23]})
        idx += 23
    else:
        layout_blocks.append({'type': 'medium', 'posts': posts[idx:]})
        idx = total

    # Repeat pattern layout: (1 scroll, 3 medium, 1 scroll, 17 medium)
    while idx < total:
        if total >= idx + 3:
            layout_blocks.append({'type': 'scroll', 'posts': posts[idx:idx+3]})
            idx += 3
        if total >= idx + 3:
            layout_blocks.append({'type': 'medium', 'posts': posts[idx:idx+3]})
            idx += 3
        if total >= idx + 3:
            layout_blocks.append({'type': 'scroll', 'posts': posts[idx:idx+3]})
            idx += 3
        if total >= idx + 17:
            layout_blocks.append({'type': 'medium', 'posts': posts[idx:idx+17]})
            idx += 17
        else:
            layout_blocks.append({'type': 'medium', 'posts': posts[idx:]})
            break

    return render(request, 'index.html', {
        'layout_blocks': layout_blocks,
        'active_page': 'frontpage',
    })



from django.shortcuts import get_object_or_404, redirect
from .models import Post, ApprovedTagAuthor
from django.contrib.auth.decorators import login_required

from django.contrib import messages


@login_required
def approve_tag_author(request, post_id):
    if request.user.username != 'migaja':  # Editor-only
        return redirect('frontpage')

    post = get_object_or_404(Post, id=post_id)

    if not post.tag:
        # Optionally, you could add a message here using Django messages framework

        messages.error(request, "This post has no tag and cannot be sent to the front page.")
        return redirect('postdetails', post_id=post.id)

    approved, created = ApprovedTagAuthor.objects.get_or_create(
        author=post.user,  # or user=post.user if your model uses `user`
        tag=post.tag
    )

    return redirect('postdetails', post_id=post.id)




@login_required
def remove_tag_author_approval(request, post_id):
    if request.user.username != 'migaja':
        return redirect('frontpage')

    post = get_object_or_404(Post, id=post_id)

    ApprovedTagAuthor.objects.filter(
        author=post.user,
        tag=post.tag
    ).delete()

    messages.success(request, "Excluded")
    return redirect('postdetails', post_id=post.id)



#11:09 7Jun25


