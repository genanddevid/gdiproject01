
from django import forms
from django.core.exceptions import ValidationError
from post.models import Post, Tag, BannerAd

class NarrativeBuilderForm(forms.ModelForm):
    
    caption = forms.CharField(widget=forms.Textarea(attrs={
        'style': 'font-size: 16px; font-family: consolas;',
        'class': 'input is-medium', 
        'placeholder': 'Write your headline...'
        }), required=True)

    content = forms.CharField(widget=forms.Textarea(attrs={
        'style': 'font-size: 16px; font-family: consolas; height: 80px;',
        'class': 'input is-medium', 
        'placeholder': 'Write your narrative...'
        }), required=True)

    tag = forms.CharField(required=False, widget=forms.HiddenInput())
        
    
    link1 = forms.URLField(widget=forms.TextInput(attrs={
        'style': 'font-size: 15px; font-family: consolas;',
        'class': 'input is-medium',
        'placeholder': 'Link 1'
        }), required=True)

    link2 = forms.URLField(widget=forms.TextInput(attrs={
        'style': 'font-size: 15px; font-family: consolas;',
        'class': 'input is-medium',
        'placeholder': 'Link 2 (optional)'
        }), required=False)        

    picture = forms.ImageField(required=True)

    class Meta:
        model = Post
        fields = ('caption', 'content', 'tag', 'link1', 'link2', 'picture')




    def __init__(self, *args, **kwargs):
        # Detect special flag to skip image requirement
        allow_missing_picture = kwargs.pop('allow_missing_picture', False)
        super().__init__(*args, **kwargs)

        if allow_missing_picture:
            self.fields['picture'].required = False





    def clean_content(self):
        content = self.cleaned_data.get('content')
        if content:
            word_count = len(content.split())
            if word_count < 250:
                raise ValidationError(f"Content must be at least 250 words (currently {word_count}).")
        return content

    def clean_tag(self):
        tag_title = self.cleaned_data['tag'].strip()
        if tag_title.startswith('#'):
            tag_title = tag_title[1:]
        tag_obj, created = Tag.objects.get_or_create(title=tag_title)
        return tag_obj

    def clean_tag(self):
        tag_title = self.cleaned_data.get('tag', '').strip()
        if not tag_title:
            return None
        if tag_title.startswith('#'):
            tag_title = tag_title[1:]
        tag_obj, created = Tag.objects.get_or_create(title=tag_title)
        return tag_obj

    def save(self, commit=True):
        instance = super().save(commit=False)
        # cleaned_data['tag'] is now a Tag instance from clean_tag()
        instance.tag = self.cleaned_data['tag']

        if commit:
            instance.save()

        return instance


    from post.models import Post, Tag, BannerAd

class BannerAdForm(forms.ModelForm):
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'input',
            'placeholder': 'Describe your product or service in one sentence...',
            'rows': 3,
        }),
        required=True
    )
    image = forms.ImageField(required=True)

    class Meta:
        model = BannerAd
        fields = ('image', 'description')




