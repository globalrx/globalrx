from django.urls import path

from . import views


app_name = "api"

urlpatterns = [
    path("v1/searchkit/_msearch", views.searchkit, name="searchkit"),
]
