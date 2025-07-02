from django import forms
from comment.models import Comment

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('body',)
        widgets = {
            'body': forms.Textarea(attrs={
                'placeholder': 'Add a comment...',
                'rows': 2,
                'class': 'textarea is-medium',  # Combined Bulma classes
            }),
        }
