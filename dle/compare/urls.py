from django.urls import path

from . import views

app_name = 'compare'
urlpatterns = [
    path('', views.index, name='index'),
    path('compare_result', views.compare_result, name='compare_result'),
]