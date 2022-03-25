from django.urls import path

from . import views

urlpatterns = [
    # e.g. "/data"
    path("", views.index, name="index"),
    # e.g. "/data/3"
    path("<int:pk>", views.SingleLabelView.as_view(), name="single_label"),
]
