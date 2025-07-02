from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from .models import Comment, CommentLike

@login_required
def like_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    user = request.user

    existing_like = CommentLike.objects.filter(user=user, comment=comment).first()

    if existing_like:
        existing_like.delete()  # Unlike
    else:
        CommentLike.objects.create(user=user, comment=comment)  # Like

    like_count = CommentLike.objects.filter(comment=comment).count()

    return JsonResponse({
        'success': True,
        'likes': like_count
    })



from django.views.decorators.http import require_POST
from .models import Comment
from django.http import HttpResponse


@login_required
@require_POST
def submit_reply(request, comment_id):
    parent_comment = get_object_or_404(Comment, id=comment_id)
    content = request.POST.get('reply', '').strip()

    if content:

        username = parent_comment.user.username
        if not content.lower().startswith(f"@{username.lower()}"):
            content = f"@{username} {content}"

        # Always attach the reply to the top-level comment (i.e., root comment)
        root_comment = parent_comment.parent if parent_comment.parent else parent_comment
        Comment.objects.create(
            post=parent_comment.post,
            user=request.user,
            body=content,
            parent=root_comment  # Assuming your Comment model has a 'parent' field
        )

    return HttpResponse(status=204)  # "No Content" response


