from django.urls import path

from . import views

app_name = 'compare'
urlpatterns = [
    path('', views.index, name='index'),
    path('list_labels', views.list_labels, name='list_labels'),
    path('compare_result', views.compare_result, name='compare_result'),
]