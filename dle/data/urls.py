from django.urls import path

from . import views

app_name = "data"

urlpatterns = [
    # e.g. "/data"
    path("", views.index, name="index"),
    # e.g. "/data/3"
    path("<int:drug_label_id>", views.single_label_view, name="single_label"),
]
