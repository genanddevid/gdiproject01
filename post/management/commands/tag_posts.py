from django.core.management.base import BaseCommand
from post.models import Post, SemanticTag
from post.views import auto_tag_post


class Command(BaseCommand):
    help = 'Auto-tag all posts that have no semantic tags'

    def handle(self, *args, **kwargs):
        untagged = Post.objects.filter(semantic_tags__isnull=True)
        total = untagged.count()
        self.stdout.write(f"Found {total} untagged posts")

        for i, post in enumerate(untagged):
            self.stdout.write(f"Tagging {i+1}/{total}: {post.caption[:50]}")
            auto_tag_post(post)

        self.stdout.write(self.style.SUCCESS("Done!"))