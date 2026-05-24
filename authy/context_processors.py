from comment.models import Comment, CommentLike
from post.models import Likes


def unread_notifications_count(request):
    if not request.user.is_authenticated:
        return {'unread_notif_count': 0}

    me = request.user
    last_seen = me.profile.notifications_last_seen

    if last_seen is None:
        # Never checked — count everything
        count = 0
        count += Likes.objects.filter(post__user=me, liked_at__isnull=False).exclude(user=me).count()
        count += Comment.objects.filter(post__user=me, parent__isnull=True).exclude(user=me).count()
        my_comment_ids = Comment.objects.filter(user=me).values_list('id', flat=True)
        count += Comment.objects.filter(parent__in=my_comment_ids).exclude(user=me).count()
        count += CommentLike.objects.filter(comment__user=me).exclude(user=me).count()
        return {'unread_notif_count': count}

    count = 0
    count += Likes.objects.filter(post__user=me, liked_at__gt=last_seen).exclude(user=me).count()
    count += Comment.objects.filter(post__user=me, parent__isnull=True, date__gt=last_seen).exclude(user=me).count()
    my_comment_ids = Comment.objects.filter(user=me).values_list('id', flat=True)
    count += Comment.objects.filter(parent__in=my_comment_ids, date__gt=last_seen).exclude(user=me).count()
    count += CommentLike.objects.filter(comment__user=me, liked_at__gt=last_seen).exclude(user=me).count()

    return {'unread_notif_count': count}
