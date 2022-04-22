from django.shortcuts import render

# Create your views here.
import decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError

# from .forms import CreateItemForm

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone

from .models import User


def index(request):
    return render(request, "users/index.html")


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            #    return HttpResponseRedirect(reverse("index"))
            return render(request, "users/index.html")

        else:
            return render(
                request,
                "users/login.html",
                {"message": "Invalid username and/or password."},
            )
    else:
        return render(request, "users/login.html")


def logout_view(request):
    # returns user to login page
    logout(request)
    return HttpResponseRedirect(reverse("login"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(
                request, "users/register.html", {"message": "Passwords must match."}
            )

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(
                request, "users/register.html", {"message": "Username already taken."}
            )
        login(request, user)
        #    return HttpResponseRedirect(reverse("index"))
        return render(request, "users/index.html")
    else:
        return render(request, "users/register.html")

@login_required
def my_labels(request):
    request.user
    return render(request, "users/my_labels.html")
