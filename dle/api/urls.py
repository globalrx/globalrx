from django.urls import path

from . import views


app_name = "api"

urlpatterns = [
    path("v1/searchkit/_msearch", views.searchkit, name="searchkit"),
    # This is used so we can reverse it in search/views.py for the search.html context
    path("v1/searchkit", views.searchkit, name="searchkit_root"),
    path("v1/vectorize", views.vectorize, name="vectorize"),
]
