

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.template import loader
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.files import File
from django.db.models import Q

import re
import math
import uuid
import os
import json

# Models
from post.models import Post, Stream, Tag, Likes, PostView, SavedItem, ApprovedTagAuthor
from authy.models import Profile
from comment.models import Comment

# Forms
from post.forms import NarrativeBuilderForm
from comment.forms import CommentForm


# ─── Helper Functions ────────────────────────────────────────────────────────

def split_into_sentences(text):
    abbreviations = r"(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|e\.g|i\.e|etc)\."
    text = re.sub(abbreviations, lambda x: x.group(0).replace('.', '<DOT>'), text)
    sentence_endings = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
    sentences = sentence_endings.split(text)
    sentences = [s.replace('<DOT>', '.') for s in sentences]
    return [s.strip() for s in sentences if s.strip()]


def divide_content(paragraphs, parts=2):
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    total = len(paragraphs)

    if total == 0:
        return [[] for _ in range(parts)]

    if total <= parts:
        result = [[] for _ in range(parts)]
        for i, p in enumerate(paragraphs):
            result[i].append(p)
        return result

    k, m = divmod(total, parts)
    result = []
    start = 0
    for i in range(parts):
        end = start + k + (1 if i < m else 0)
        result.append(paragraphs[start:end])
        start = end

    for i in range(len(result) - 1):
        if len(result[i]) == 0 and len(result[i + 1]) > 1:
            result[i].append(result[i + 1].pop(0))

    return result


def split_content_for_post(post):
    """Split post content into parts around video embeds."""
    raw_paragraphs = re.split(r'\n\s*\n+', post.content.strip())
    paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]

    if post.link1 and post.link2:
        split_parts = divide_content(paragraphs, parts=3)
    elif post.link1:
        split_parts = divide_content(paragraphs, parts=2)
    else:
        split_parts = [paragraphs]

    split_parts = ['\n\n'.join(part) for part in split_parts if part]

    return (
        split_parts[0] if len(split_parts) >= 1 else '',
        split_parts[1] if len(split_parts) >= 2 else '',
        split_parts[2] if len(split_parts) >= 3 else '',
    )


def get_recommendations(post, user):
    """Get left and right recommendations excluding current post."""
    if user.is_authenticated:
        all_other_posts = Post.objects.exclude(id=post.id).exclude(user=user).order_by('id')
    else:
        all_other_posts = Post.objects.exclude(id=post.id).order_by('id')

    left_recommendations = []
    right_recommendations = []

    for i, p in enumerate(all_other_posts):
        if len(left_recommendations) >= 3 and len(right_recommendations) >= 3:
            break
        if i % 2 == 0 and len(left_recommendations) < 3:
            left_recommendations.append(p)
        elif i % 2 == 1 and len(right_recommendations) < 3:
            right_recommendations.append(p)

    return left_recommendations, right_recommendations


# ─── Views ───────────────────────────────────────────────────────────────────

def index(request):
    approved_combos = ApprovedTagAuthor.objects.all()

    if approved_combos.exists():
        query = Q()
        for combo in approved_combos:
            query |= Q(user=combo.author, tag=combo.tag)
        posts = Post.objects.filter(query).order_by('-posted')
    else:
        posts = Post.objects.none()

    posts = list(posts)
    layout_blocks = []
    idx = 0
    total = len(posts)

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


def interests_view(request):
    if not request.user.is_authenticated:
        post_items = Post.objects.none()
    else:
        posts = Stream.objects.filter(user=request.user)
        group_ids = [post.post_id for post in posts]
        post_items = Post.objects.filter(id__in=group_ids).order_by('-posted')

    template = loader.get_template('interests.html')
    context = {
        'post_items': post_items,
        'active_page': 'interests',
    }
    return HttpResponse(template.render(context, request))



def PostDetails(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # Detect if request is from a social media scraper (WhatsApp, Facebook etc.)
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    scrapers = ['whatsapp', 'facebookexternalhit', 'twitterbot', 'linkedinbot', 'telegrambot', 'slackbot']
    
    is_scraper = any(scraper in user_agent for scraper in scrapers)
    
    if is_scraper:
        # Serve OG tags page for scrapers
        return render(request, 'post_og.html', {'post': post})
    
    # Regular users get redirected to frontpage with modal
    return redirect(f'/?open={post_id}')
    


def post_modal(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    user = request.user

    if user.is_authenticated:
    PostView.objects.get_or_create(user=user, post=post)
    
    # Record interest from semantic tags
    from post.models import SemanticTag, UserInterest
    semantic_tags = SemanticTag.objects.filter(post=post)
    for tag in semantic_tags:
        interest, created = UserInterest.objects.get_or_create(
            user=user,
            entity=tag.entity,
            defaults={
                'category': tag.category,
                'parent_category': tag.parent_category,
                'grandparent_category': tag.grandparent_category,
                'semantic_labels': tag.semantic_labels,
                'click_count': 1,
            }
        )
        if not created:
            interest.click_count += 1
            interest.save()

    liked = Likes.objects.filter(user=user, post=post).exists() if user.is_authenticated else False
    form = CommentForm()
    favorited = False
    comments = Comment.objects.filter(post=post).order_by('date')

    if request.method == 'POST' and user.is_authenticated:
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.user = user
            comment.save()
            form = CommentForm()
            comments = Comment.objects.filter(post=post).order_by('date')

    if user.is_authenticated:
        profile = Profile.objects.get(user=user)
        if profile.favorites.filter(id=post_id).exists():
            favorited = True

    total_comment_count = Comment.objects.filter(post=post).count()
    left_recommendations, right_recommendations = get_recommendations(post, user)
    content1, content2, content3 = split_content_for_post(post)

    is_approved = ApprovedTagAuthor.objects.filter(
        author=post.user, tag=post.tag
    ).exists()

    return render(request, 'post_detail_modal.html', {
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
    })


@login_required
def NarrativeBuilder(request):
    if request.method == "POST":
        form = NarrativeBuilderForm(request.POST, request.FILES)
        if form.is_valid():
            post_instance = form.save(commit=False)
            post_instance.user = request.user
            post_instance.save()
            request.session.pop('preview_data', None)
            return redirect(reverse('profile', kwargs={'username': request.user.username}))
    else:
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

    return render(request, 'narrativebuilder.html', {
        'form': form,
        'active_page': 'narrativebuilder',
    })


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
            elif instance and instance.picture:
                temp_image_url = instance.picture.url    

            post = form.save(commit=False)
            post.user = request.user

            raw_paragraphs = re.split(r'\n\s*\n+', post.content.strip())
            paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]

            if post.link1 and post.link2:
                split_parts = divide_content(paragraphs, parts=3)
            elif post.link1:
                split_parts = divide_content(paragraphs, parts=2)
            else:
                split_parts = [paragraphs]

            split_parts = ['\n\n'.join(part) if isinstance(part, list) else part for part in split_parts if part]

            return render(request, 'narrative_preview.html', {
                'post': post,
                'image_url': temp_image_url,
                'edit_mode': bool(post_id),
                'post_id': post_id,
                'content1': split_parts[0] if len(split_parts) >= 1 else '',
                'content2': split_parts[1] if len(split_parts) >= 2 else '',
                'content3': split_parts[2] if len(split_parts) >= 3 else '',
            })

    if post_id:
        return redirect('edit_post', post_id=post_id)
    return redirect('narrativebuilder')


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

    return HttpResponse(status=204)


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
    return render(request, 'all_collections.html')


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, user=request.user)
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
            return redirect('profile', username=request.user.username)
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
            del request.session['preview_data']
        else:
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
        picture_path = preview_data.pop('picture', None)
        form = NarrativeBuilderForm(data=preview_data, instance=post, allow_missing_picture=True)

        if form.is_valid():
            updated_post = form.save(commit=False)
            if picture_path:
                with default_storage.open(picture_path, 'rb') as f:
                    updated_post.picture.save(picture_path.split('/')[-1], File(f))
            updated_post.save()
            request.session.pop('preview_data', None)
            return redirect('profile', username=request.user.username)

    return redirect('edit_post', post_id=post_id)


@login_required
def finalize_new_post(request):
    preview_data = request.session.get('preview_data')

    if request.method == 'POST' and preview_data:
        picture_path = preview_data.pop('picture', None)
        form = NarrativeBuilderForm(data=preview_data, allow_missing_picture=True)

        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            if picture_path:
                with default_storage.open(picture_path, 'rb') as f:
                    post.picture.save(picture_path.split('/')[-1], File(f))
            post.save()
            request.session.pop('preview_data', None)
            return redirect('profile', username=request.user.username)

    return redirect('narrativebuilder')


@login_required
def view_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    PostView.objects.get_or_create(user=request.user, post=post)
    return redirect('postdetails', post_id=post_id)


@login_required
def approve_tag_author(request, post_id):
    if request.user.username != 'migaja':
        return redirect('frontpage')

    post = get_object_or_404(Post, id=post_id)
    if not post.tag:
        messages.error(request, "This post has no tag and cannot be sent to the front page.")
        return redirect('postdetails', post_id=post.id)

    ApprovedTagAuthor.objects.get_or_create(author=post.user, tag=post.tag)
    return redirect('postdetails', post_id=post.id)


@login_required
def remove_tag_author_approval(request, post_id):
    if request.user.username != 'migaja':
        return redirect('frontpage')

    post = get_object_or_404(Post, id=post_id)
    ApprovedTagAuthor.objects.filter(author=post.user, tag=post.tag).delete()
    messages.success(request, "Excluded")
    return redirect('postdetails', post_id=post.id)



def auto_tag_post(post):
    try:
        from groq import Groq
        from post.models import SemanticTag

        client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """Extract named entities from this headline and return ONLY valid JSON. No explanations, no extra text.

Classify each entity using a hybrid ontology:

1. HIERARCHY (strict parent-child chain, stop when next level becomes artificial):
   Daniel Dubois → Heavyweight Boxing → Boxing → Combat Sports → Sports
   Cristiano Ronaldo → Football → Sports
   Jerome Powell → Monetary Policy → Central Banking → Economics

2. SEMANTIC LABELS (flat, non-hierarchical — profession, identity, domain):
   Elon Musk → labels: Entrepreneur, Tech Billionaire, AI Industry, Space Technology
   Daniel Dubois → labels: Professional Boxer, Heavyweight Athlete

Rules:
- Extract from headline only
- NEVER use generic labels like Person, Individual, Human, Thing, Place
- Allow uneven depth — don't force equal levels
- One entity can belong to multiple semantic labels simultaneously

Return ONLY this JSON structure:
{
  "tags": [
    {
      "entity": "Name",
      "category": "Most specific domain",
      "parent_category": "Broader category or null",
      "grandparent_category": "Broadest category or null",
      "semantic_labels": ["label1", "label2"]
    }
  ]
}
Maximum 8 entities."""
                },
                {
                    "role": "user",
                    "content": f"Headline: {post.caption}"
                }
            ],
            temperature=0.3,
            max_tokens=600,
        )

        response_text = completion.choices[0].message.content.strip()
        if '```' in response_text:
            response_text = response_text.split('```')[1].replace('json', '').strip()

        data = json.loads(response_text)
        SemanticTag.objects.filter(post=post).delete()

        for tag in data.get('tags', []):
            labels = tag.get('semantic_labels', [])
            SemanticTag.objects.create(
                post=post,
                entity=tag.get('entity', ''),
                category=tag.get('category', ''),
                parent_category=tag.get('parent_category', '') or '',
                grandparent_category=tag.get('grandparent_category', '') or '',
                semantic_labels=', '.join(labels) if labels else ''
            )
        print(f"Tagged: {post.caption[:50]}")
    except Exception as e:
        print(f"Tagging failed for {post.id}: {e}")




def improve_writing(request):
    if request.method == 'POST':
        import json
        from groq import Groq
        try:
            data = json.loads(request.body)
            original_text = data.get('text', '')
            
            if not original_text.strip():
                return JsonResponse({'error': 'No text provided'}, status=400)
            
            api_key = os.environ.get('GROQ_API_KEY')
            if not api_key:
                return JsonResponse({'error': 'API key not configured'}, status=500)
            
            client = Groq(api_key=api_key)
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert editor for Baytruyen, a news-style writing platform. 
                        Improve the writer's text while preserving their voice, facts and meaning.
                        - Fix grammar and spelling errors
                        - Improve sentence structure and flow
                        - Make it read like a professional news article
                        - Keep the same facts and story
                        - Return only the improved text, no explanations"""
                    },
                    {
                        "role": "user", 
                        "content": f"Please improve this writing:\n\n{original_text}"
                    }
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            
            improved_text = completion.choices[0].message.content
            return JsonResponse({'improved': improved_text})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)




@login_required  
def run_tagging_now(request):
    try:
        from post.models import Post, SemanticTag
        
        untagged = list(Post.objects.filter(semantic_tags__isnull=True)[:3])
        count = len(untagged)
        
        tagged = 0
        skipped = 0
        skipped_ids = []
        
        for post in untagged:
            try:
                auto_tag_post(post)
                # Check if tags were actually created
                if SemanticTag.objects.filter(post=post).exists():
                    tagged += 1
                else:
                    # Force a dummy tag so it doesn't loop forever
                    SemanticTag.objects.create(
                        post=post,
                        entity='untagged',
                        category='untagged',
                        semantic_labels='failed'
                    )
                    skipped += 1
                    skipped_ids.append(str(post.id)[:8])
            except Exception as e:
                skipped += 1
                skipped_ids.append(str(post.id)[:8])
        
        remaining = Post.objects.filter(semantic_tags__isnull=True).count()
        return HttpResponse(
            f'Tagged {tagged}, skipped {skipped} posts. '
            f'{remaining} remaining. '
            f'Skipped IDs: {skipped_ids}. Refresh to continue.'
        )
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}')







    
