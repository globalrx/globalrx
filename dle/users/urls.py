from django.urls import path
from . import views
from dle import settings
from django.conf.urls.static import static

urlpatterns = [
    # url pattern referencing workflow of overall app
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register, name="register")
    # path("newitem", views.newitem, name="newitem"),
    # path("items/<int:item_id>", views.item, name="item"),
    # path("items/<int:item_id>/tracking", views.tracking, name="tracking"),
    # path("requested", views.requesteditem, name="requesteditem"),
    # path("requesteditem/add", views.requesteditem_add, name="requesteditem_add"),
    # path("requesteditem/delete", views.requesteditem_delete, name="requesteditem_delete")
]
