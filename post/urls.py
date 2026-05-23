from django.urls import path
from . import views
from post.views import index, NarrativeBuilder, PostDetails, like, favorite, preview_narrative, ad_dashboard, approve_ad, reject_ad, delete_ad
from .views import remove_writer_entity


urlpatterns = [
    path('', views.index, name='index'),
    path('narrative-builder/', views.NarrativeBuilder, name='narrativebuilder'),  # ✅ Ensure this is included
    path('preview/', preview_narrative, name='preview_narrative'),
    path('preview/<uuid:post_id>/', preview_narrative, name='preview_narrative'),

    
    path('preview/<uuid:post_id>/publish/', views.finalize_edit, name='finalize_edit'),
    path('preview/publish/', views.finalize_new_post, name='finalize_new_post'),


    path('<uuid:post_id>', PostDetails, name='postdetails'),
    path('<uuid:post_id>/like', like, name='postlike'),
    path('<uuid:post_id>/favorite', favorite, name='postfavorite'),

     # ... your other post URLs
    path('delete/<uuid:post_id>/', views.delete_post, name='delete_post'),
    path('narrativebuilder/edit/<uuid:post_id>/', views.edit_post, name='edit_post'), 

      # ✅ New route to track post views
    path('<uuid:post_id>/view/', views.view_post, name='view_post'),

    path('approve/<uuid:post_id>/', views.approve_writer_entity, name='approve_writer_entity'),

    path('remove-approval/<uuid:post_id>/', views.remove_writer_entity, name='remove_writer_entity'),

    path('modal/<uuid:post_id>/', views.post_modal, name='post_modal'),

    path('ads/', ad_dashboard, name='ad_dashboard'),
    path('ads/approve/<int:ad_id>/', approve_ad, name='approve_ad'),
    path('ads/reject/<int:ad_id>/', reject_ad, name='reject_ad'),
    path('ads/delete/<int:ad_id>/', delete_ad, name='delete_ad'),

    




    
]


#11:09 7Jun25