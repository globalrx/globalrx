from django.urls import path

from . import views


app_name = "data"
urlpatterns = [
    path("", views.index, name="index"),
    path(
        "single_label_view/<int:drug_label_id>", views.single_label_view, name="single_label_view"
    ),
    path(
        "single_label_view/<int:drug_label_id>, <str:search_text>",
        views.single_label_view,
        name="single_label_view",
    ),
    path("visualizations", views.visualizations, name="dataviz"),
    path("search_label_htmx", views.search_label_htmx, name="search_label_htmx"),
]
