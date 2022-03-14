from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("results", views.list_search_results, name="list_search_results"),
]
