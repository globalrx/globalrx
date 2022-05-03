from django.urls import path

from . import views

app_name = 'compare'
urlpatterns = [
    path('compare_labels', views.compare_labels, name='compare_labels'),
    path('compare_versions', views.compare_versions, name='compare_versions'),
]