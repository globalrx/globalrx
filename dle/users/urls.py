from django.urls import path
from . import views
from dle import settings
from django.conf.urls.static import static

urlpatterns = [
    # url pattern referencing workflow of overall app
    # path("", views.index, name="index"), # TODO
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register, name="register"),
    path("my_labels/", views.my_labels, name="my_labels"),
]
