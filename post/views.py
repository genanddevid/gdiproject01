

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
from django.db import models
from django.core.cache import cache

import re
import math
import uuid
import os
import json
import requests
from bs4 import BeautifulSoup

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
    """Get recommendations based on entity and category matches - 50/50 split."""
    from post.models import SemanticTag
    
    try:
        # Get current post's entities and categories
        current_tags = SemanticTag.objects.filter(post=post)
        current_entities = set(current_tags.values_list('entity', flat=True))
        current_categories = set(current_tags.values_list('category', flat=True))
        
        # If no tags found fall back immediately
        if not current_entities and not current_categories:
            base_exclude = Post.objects.exclude(id=post.id)
            if user.is_authenticated:
                base_exclude = base_exclude.exclude(user=user)
            fallback = list(base_exclude.order_by('-likes')[:6])
            return fallback[:3], fallback[3:]
        
        # Base exclusions
        base_exclude = Post.objects.exclude(id=post.id)
        if user.is_authenticated:
            base_exclude = base_exclude.exclude(user=user)
        
        # 50% — same entity posts
        entity_matched_ids = set(
            SemanticTag.objects.filter(entity__in=current_entities)
            .exclude(post=post)
            .values_list('post_id', flat=True)
        )
        entity_posts = list(
            base_exclude.filter(id__in=entity_matched_ids)
            .order_by('-likes')[:6]
        )
        
        # 50% — same category posts (excluding entity matches)
        category_matched_ids = set(
            SemanticTag.objects.filter(category__in=current_categories)
            .exclude(post=post)
            .values_list('post_id', flat=True)
        ) - entity_matched_ids
        
        category_posts = list(
            base_exclude.filter(id__in=category_matched_ids)
            .order_by('-likes')[:6]
        )
        
        # If not enough matches fall back to liked posts
        if not entity_posts and not category_posts:
            fallback = list(base_exclude.order_by('-likes')[:6])
            return fallback[:3], fallback[3:]
        
        # Interleave entity and category posts
        combined = []
        max_len = max(len(entity_posts), len(category_posts))
        for i in range(max_len):
            if i < len(entity_posts):
                combined.append(entity_posts[i])
            if i < len(category_posts):
                combined.append(category_posts[i])
        
        # Remove duplicates
        seen = set()
        unique_combined = []
        for p in combined:
            if p.id not in seen:
                seen.add(p.id)
                unique_combined.append(p)
        
        # Split into left and right
        mid = len(unique_combined) // 2
        left_recommendations = unique_combined[:mid]
        right_recommendations = unique_combined[mid:]
        
        return left_recommendations, right_recommendations
        
    except Exception as e:
        # Silent fallback — never let recommendations break article loading
        print(f"Recommendations failed: {e}")
        base_exclude = Post.objects.exclude(id=post.id)
        fallback = list(base_exclude.order_by('-likes')[:6])
        return fallback[:3], fallback[3:]








# ─── Views ───────────────────────────────────────────────────────────────────

def index(request):
    from post.models import ApprovedWriterEntity, SemanticTag

    # Try cache first — avoid rebuilding on every request
    cached_posts = cache.get('frontpage_posts')
    
    if cached_posts is None:
        approved = ApprovedWriterEntity.objects.all()
        
        if approved.exists():
            all_tags = SemanticTag.objects.values('post_id', 'entity')
            post_entity_map = {}
            for tag in all_tags:
                pid = tag['post_id']
                if pid not in post_entity_map:
                    post_entity_map[pid] = set()
                post_entity_map[pid].add(tag['entity'])
            
            writer_entity_map = {}
            for combo in approved:
                wid = combo.writer_id
                if wid not in writer_entity_map:
                    writer_entity_map[wid] = set()
                writer_entity_map[wid].add(combo.entity)
            
            approved_post_ids = set()
            for post in Post.objects.only('id', 'user_id'):
                post_entities = post_entity_map.get(post.id, set())
                writer_approved = writer_entity_map.get(post.user_id, set())
                if post_entities & writer_approved:
                    approved_post_ids.add(post.id)
            
            cached_posts = list(
                Post.objects.filter(
                    id__in=approved_post_ids
                ).select_related('user__profile').order_by('-posted')
            )
        else:
            cached_posts = []
        
        # Cache for 5 minutes
        cache.set('frontpage_posts', cached_posts, 300)
    
    posts = cached_posts
    layout_blocks = []
    idx = 0
    total = len(posts)

    if total >= 1:
        layout_blocks.append({'type': 'large', 'posts': posts[idx:idx+1]})
        idx += 1
    if total >= idx + 5:
        layout_blocks.append({'type': 'scroll', 'posts': posts[idx:idx+4]})
        idx += 5
    if total >= idx + 2:
        layout_blocks.append({'type': 'large', 'posts': posts[idx:idx+2]})
        idx += 2
    if total >= idx + 43:
        layout_blocks.append({'type': 'medium', 'posts': posts[idx:idx+23]})
        idx += 43
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
        return render(request, 'interests.html', {
            'post_items': [],
            'active_page': 'interests',
        })

    from post.models import UserInterest, SemanticTag
    import random
    from django.utils import timezone

    user = request.user
    now = timezone.now()

    try:
        user_interests = UserInterest.objects.filter(user=user)
        interest_entities = set(ui.entity for ui in user_interests)
        interest_categories = set(ui.category for ui in user_interests)

        followed_posts = Stream.objects.filter(user=user)
        followed_post_ids = set(s.post_id for s in followed_posts)

        entity_matched_ids = set(
            SemanticTag.objects.filter(entity__in=interest_entities)
            .values_list('post_id', flat=True)
        ) if interest_entities else set()

        category_matched_ids = set(
            SemanticTag.objects.filter(category__in=interest_categories)
            .values_list('post_id', flat=True)
        ) if interest_categories else set()

        all_relevant_ids = followed_post_ids | entity_matched_ids | category_matched_ids

        if not all_relevant_ids:
            return render(request, 'interests.html', {
                'post_items': [],
                'active_page': 'interests',
            })

        # ONE query — pre-fetch all semantic tags for relevant posts
        all_relevant_tags = SemanticTag.objects.filter(
            post_id__in=all_relevant_ids
        ).values('post_id', 'entity', 'category')
        
        post_entity_map = {}
        post_category_map = {}
        for tag in all_relevant_tags:
            pid = tag['post_id']
            if pid not in post_entity_map:
                post_entity_map[pid] = set()
                post_category_map[pid] = set()
            post_entity_map[pid].add(tag['entity'])
            post_category_map[pid].add(tag['category'])

        all_posts = Post.objects.filter(
            id__in=all_relevant_ids
        ).exclude(user=user).select_related('user__profile')

        scored_posts = []
        for i, post in enumerate(all_posts):
            try:
                score = 0

                try:
                    age = (now - post.posted).days
                    if age <= 7:
                        score += 5
                    elif age <= 30:
                        score += 2
                except Exception:
                    pass

                score += post.likes

                if post.id in followed_post_ids:
                    score += 2

                post_entities = post_entity_map.get(post.id, set())
                if post_entities & interest_entities:
                    score += 3

                post_categories = post_category_map.get(post.id, set())
                if post_categories & interest_categories:
                    score += 2

                if i % 4 == 3:
                    score += random.randint(1, 3)

                scored_posts.append((score, post))

            except Exception:
                continue

        scored_posts.sort(key=lambda x: x[0], reverse=True)
        post_items = [post for score, post in scored_posts]

    except Exception as e:
        print(f"Interests feed error: {e}")
        post_items = []

    return render(request, 'interests.html', {
        'post_items': post_items,
        'active_page': 'interests',
    })




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
    


def get_matching_ad(post):
    """Find an approved ad whose entities match the post's semantic tags"""
    try:
        from post.models import SemanticTag, BannerAd
        
        post_entities = set(
            SemanticTag.objects.filter(post=post)
            .values_list('entity', flat=True)
        )
        post_categories = set(
            SemanticTag.objects.filter(post=post)
            .values_list('category', flat=True)
        )
        
        approved_ads = BannerAd.objects.filter(status='approved')
        
        matched_ads = []
        for ad in approved_ads:
            ad_entities = set(e.strip().lower() for e in ad.entities.split(',') if e.strip())
            post_entities_lower = set(e.lower() for e in post_entities)
            post_categories_lower = set(c.lower() for c in post_categories)
            
            if ad_entities & (post_entities_lower | post_categories_lower):
                matched_ads.append(ad)
        
        if matched_ads:
            # Return up to 2 matched ads
            return matched_ads[:2]
        return []
    except Exception as e:
        print(f"Ad matching failed: {e}")
        return []


def get_tiktok_thumbnail(url):
    """Resolve TikTok short URL and fetch thumbnail via oEmbed"""
    try:
        import requests as req
        
        # Resolve short URLs like vt.tiktok.com
        if 'vt.tiktok.com' in url or 'vm.tiktok.com' in url:
            response = req.get(url, allow_redirects=True, timeout=5)
            url = response.url
        
        # Call TikTok oEmbed API
        oembed_url = f"https://www.tiktok.com/oembed?url={url}"
        response = req.get(oembed_url, timeout=5)
        data = response.json()
        
        return {
            'thumbnail': data.get('thumbnail_url', ''),
            'title': data.get('title', ''),
            'url': url,
        }
    except Exception as e:
        print(f"TikTok oEmbed failed: {e}")
        return None





def post_modal(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    user = request.user

    if user.is_authenticated:
        PostView.objects.get_or_create(user=user, post=post)
    
        # Record interest only on explicit opens
        if request.method == 'GET' and request.GET.get('track') == '1':
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
    comments = Comment.objects.filter(post=post).select_related(
        'user__profile'
    ).prefetch_related('replies__user__profile', 'likes').order_by('date')
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
    # TikTok thumbnail fetching
    tiktok1 = None
    tiktok2 = None
    if post.link1 and 'tiktok.com' in post.link1:
        tiktok1 = get_tiktok_thumbnail(post.link1)
    if post.link2 and 'tiktok.com' in post.link2:
        tiktok2 = get_tiktok_thumbnail(post.link2)
    matched_ads = get_matching_ad(post)
    ad1 = matched_ads[0] if len(matched_ads) >= 1 else None
    ad2 = matched_ads[1] if len(matched_ads) >= 2 else None

    # Increment impressions
    from post.models import BannerAd
    for ad in matched_ads:
        BannerAd.objects.filter(id=ad.id).update(impressions=models.F('impressions') + 1)

    from post.models import SemanticTag, ApprovedWriterEntity
    post_entities = set(
        SemanticTag.objects.filter(post=post)
        .values_list('entity', flat=True)
    )
    writer_approved_entities = set(
        ApprovedWriterEntity.objects.filter(writer=post.user)
        .values_list('entity', flat=True)
    )
    is_approved = bool(post_entities & writer_approved_entities)

    return render(request, 'post_detail_modal.html', {
        'post': post,
        'liked': liked,
        'tiktok1': tiktok1,
        'tiktok2': tiktok2,
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
        'ad1': ad1,
        'ad2': ad2,
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

            # TikTok thumbnail fetching for preview
            tiktok1 = None
            tiktok2 = None
            link1 = form.cleaned_data.get('link1', '')
            link2 = form.cleaned_data.get('link2', '')
            if link1 and 'tiktok.com' in link1:
                tiktok1 = get_tiktok_thumbnail(link1)
            if link2 and 'tiktok.com' in link2:
                tiktok2 = get_tiktok_thumbnail(link2)

            return render(request, 'narrative_preview.html', {
                'post': post,
                'image_url': temp_image_url,
                'edit_mode': bool(post_id),
                'post_id': post_id,
                'content1': split_parts[0] if len(split_parts) >= 1 else '',
                'content2': split_parts[1] if len(split_parts) >= 2 else '',
                'content3': split_parts[2] if len(split_parts) >= 3 else '',
                'tiktok1': tiktok1,
                'tiktok2': tiktok2,
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
            try:
                auto_tag_post(updated_post)
            except Exception as e:
                print(f"Auto-tagging failed silently: {e}")
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
            # Auto-tag in background — silent fail so publishing is never blocked
            try:
                auto_tag_post(post)
            except Exception as e:
                print(f"Auto-tagging failed silently: {e}")
            request.session.pop('preview_data', None)
            return redirect('profile', username=request.user.username)

    return redirect('narrativebuilder')


@login_required
def view_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    PostView.objects.get_or_create(user=request.user, post=post)
    return redirect('postdetails', post_id=post_id)


@login_required
def approve_writer_entity(request, post_id):
    if request.user.username != 'migaja':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    post = get_object_or_404(Post, id=post_id)
    
    if request.method == 'POST':
        import json
        from post.models import ApprovedWriterEntity
        data = json.loads(request.body)
        entities = data.get('entities', [])
        
        for entity in entities:
            ApprovedWriterEntity.objects.get_or_create(
                writer=post.user,
                entity=entity
            )
        
        cache.delete('frontpage_posts')
        return JsonResponse({'success': True, 'approved': entities})
    
    # GET — return current entities for this post
    from post.models import SemanticTag, ApprovedWriterEntity
    post_entities = list(
        SemanticTag.objects.filter(post=post)
        .values('entity', 'category')
    )
    approved_entities = set(
        ApprovedWriterEntity.objects.filter(writer=post.user)
        .values_list('entity', flat=True)
    )
    
    return JsonResponse({
        'post_entities': post_entities,
        'approved_entities': list(approved_entities)
    })


@login_required
def remove_writer_entity(request, post_id):
    if request.user.username != 'migaja':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    post = get_object_or_404(Post, id=post_id)
    
    if request.method == 'POST':
        import json
        from post.models import ApprovedWriterEntity
        data = json.loads(request.body)
        entities = data.get('entities', [])
        
        ApprovedWriterEntity.objects.filter(
            writer=post.user,
            entity__in=entities
        ).delete()
        
        cache.delete('frontpage_posts')
        return JsonResponse({'success': True, 'removed': entities})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)







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

@login_required
def ad_dashboard(request):
    from post.models import BannerAd
    from post.forms import BannerAdForm
    
    if request.method == 'POST':
        form = BannerAdForm(request.POST, request.FILES)
        if form.is_valid():
            ad = form.save(commit=False)
            ad.advertiser = request.user
            
            # Resize image to 300x250
            from PIL import Image as PILImage
            from io import BytesIO
            from django.core.files.base import ContentFile
            
            img = PILImage.open(ad.image)
            img = img.convert('RGB')
            img = img.resize((360, 360), PILImage.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            ad.image.save(
                f"ad_{request.user.id}_{uuid.uuid4()}.jpg",
                ContentFile(buffer.read()),
                save=False
            )
            
            # Extract entities using Groq
            try:
                from groq import Groq
                client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system",
                            "content": """Extract relevant entities and topics from this ad description.
Return ONLY a comma-separated list of entities/topics. No other text.
Example: 'boxing gloves, fitness, sports equipment, training'
Maximum 6 entities."""
                        },
                        {
                            "role": "user",
                            "content": f"Ad description: {ad.description}"
                        }
                    ],
                    temperature=0.3,
                    max_tokens=100,
                )
                ad.entities = completion.choices[0].message.content.strip()
            except Exception as e:
                print(f"Ad entity extraction failed: {e}")
                ad.entities = ''
            
            ad.save()
            return redirect('ad_dashboard')
    else:
        form = BannerAdForm()
    
    user_ads = BannerAd.objects.filter(advertiser=request.user).order_by('-created_at')
    
    # Migaja sees all pending ads
    pending_ads = None
    if request.user.username == 'migaja':
        pending_ads = BannerAd.objects.filter(status='pending').order_by('-created_at')
    
    return render(request, 'ads_dashboard.html', {
        'form': form,
        'user_ads': user_ads,
        'pending_ads': pending_ads,
    })


@login_required
def approve_ad(request, ad_id):
    if request.user.username != 'migaja':
        return HttpResponse('Unauthorized', status=403)
    from post.models import BannerAd
    ad = get_object_or_404(BannerAd, id=ad_id)
    ad.status = 'approved'
    ad.save()
    return redirect('ad_dashboard')


@login_required
def reject_ad(request, ad_id):
    if request.user.username != 'migaja':
        return HttpResponse('Unauthorized', status=403)
    from post.models import BannerAd
    ad = get_object_or_404(BannerAd, id=ad_id)
    ad.status = 'rejected'
    ad.save()
    return redirect('ad_dashboard')


@login_required
def delete_ad(request, ad_id):
    from post.models import BannerAd
    ad = get_object_or_404(BannerAd, id=ad_id, advertiser=request.user)
    ad.image.delete()
    ad.delete()
    return redirect('ad_dashboard')



def writeword_explain(request):
    if request.method == 'POST':
        try:
            from groq import Groq
            data = json.loads(request.body)
            word = data.get('word', '').strip()
            
            if not word:
                return JsonResponse({'error': 'No word provided'}, status=400)
            
            client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a concise encyclopedia. When given a name or entity, 
provide exactly 1-2 sentences that are factual, neutral and informative.
Cover who or what it is, why it is notable, and one key fact.
Return only the explanation — no preamble, no labels."""
                    },
                    {
                        "role": "user",
                        "content": f"Explain: {word}"
                    }
                ],
                temperature=0.3,
                max_tokens=120,
            )
            explanation = completion.choices[0].message.content.strip()
            return JsonResponse({'explanation': explanation})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)



def vocabulary_lookup(request):
    word = request.GET.get('word', '').strip()

    if not word:
        return JsonResponse({'definition': None})

    try:
        url = f"https://www.vocabulary.com/dictionary/{word}"

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            return JsonResponse({'definition': None})

        soup = BeautifulSoup(response.text, 'html.parser')

        definition = None

        short_def = soup.select_one('.short')
        pos_tag = soup.select_one('.pos-icon')

        definition = None
        part_of_speech = None

        if short_def:
            definition = short_def.get_text(" ", strip=True)

        if pos_tag:
            part_of_speech = pos_tag.get_text(" ", strip=True)

        return JsonResponse({
            'definition': definition,
            'partOfSpeech': part_of_speech
        })

    except Exception as e:
        return JsonResponse({
            'definition': None,
            'error': str(e)
        })


def wordreference_lookup(request):
    word = request.GET.get('word', '').strip()

    if not word:
        return JsonResponse({'definition': None})

    try:
        url = f"https://www.wordreference.com/definition/{word}"

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            return JsonResponse({'definition': None})

        soup = BeautifulSoup(response.text, 'html.parser')

        definition = None
        definition_tag = soup.select_one('span.rh_def')
        pos_tag = soup.select_one('span.rh_empos')

        definition = None
        part_of_speech = None

        if definition_tag:

            definition_copy = BeautifulSoup(
                str(definition_tag),
                'html.parser'
            )

            for tag in definition_copy.select('.rh_ex, .rh_lab'):
                tag.decompose()

            definition = definition_copy.get_text(" ", strip=True)

        if pos_tag:
            part_of_speech = pos_tag.get_text(" ", strip=True)
        return JsonResponse({
            'definition': definition,
            'partOfSpeech': part_of_speech
        })

    except Exception as e:
        return JsonResponse({
            'definition': None,
            'error': str(e)
        })


import requests
from bs4 import BeautifulSoup


def cambridge_lookup(request):
    word = request.GET.get("word", "").strip()

    if not word:
        return JsonResponse({"error": "Missing word"}, status=400)

    url = f"https://dictionary.cambridge.org/dictionary/english/{word}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/137.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return JsonResponse({
                "pronunciation": "",
                "source": "Cambridge"
            })

        soup = BeautifulSoup(response.text, "html.parser")

        ipa = soup.select_one(".ipa")

        pronunciation = ipa.get_text(" ", strip=True) if ipa else ""

        return JsonResponse({
            "pronunciation": pronunciation,
            "source": "Cambridge"
        })

    except Exception:
        return JsonResponse({
            "pronunciation": "",
            "source": "Cambridge"
        })


    
