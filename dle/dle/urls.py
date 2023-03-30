"""dle URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import include, path


# from django.contrib import admin


def redirect_from_root_view(request: HttpRequest):
    """Redirects requests to rootpath to the search endpoint."""
    return redirect("/search")


urlpatterns = [
    # path("admin/", admin.site.urls),
    path("users/", include("users.urls")),
    path("data/", include("data.urls")),
    path("", redirect_from_root_view),
    path("search/", include("search.urls")),
    path("compare/", include("compare.urls")),
    path("api/", include("api.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
