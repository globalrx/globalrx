from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import User, MyLabel
from data.models import DrugLabel
from .forms import MyLabelForm
import datetime as dt
from django.core import management
from django.db import connection


@login_required
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
            return redirect(reverse("users:index"))

        else:
            return render(
                request,
                "users/login.html",
                {"message": "Invalid username and/or password."},
            )
    else:
        return render(request, "users/login.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect(reverse("users:login"))


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
        return redirect(reverse("users:index"))
    else:
        return render(request, "users/register.html")


@login_required
def my_labels_view(request, msg=None):
    # create a blank form for the user to create a new my_label
    form = MyLabelForm()
    # get a list of the user's MyLabels
    # note, could have performance issues if user has a "lot" of labels
    my_labels = MyLabel.objects.filter(user=request.user).all()
    context = {
        "form": form,
        "my_labels": my_labels,
        "message": msg,
    }
    return render(request, "users/my_labels.html", context)


@login_required
def create_my_label(request):
    """Accepts a request for a user to create a new MyLabel"""
    if request.method == "POST":
        form = MyLabelForm(request.POST, request.FILES)

        if form.is_valid():
            file_name_suffix = form.cleaned_data["file"].name.split(".")[-1]
            supported_filetypes = ["pdf", "xml"]
            if file_name_suffix not in supported_filetypes:
                msg = "File must be one of: " + str(supported_filetypes)
                return my_labels_view(request, msg)

            if form.cleaned_data["source"] == "EMA" and file_name_suffix != "pdf":
                msg = "Only pdf files are supported for EMA drug labels"
                return my_labels_view(request, msg)

            if form.cleaned_data["source"] == "FDA" and file_name_suffix != "xml":
                msg = "Only xml files are supported for FDA drug labels"
                return my_labels_view(request, msg)

            # create a DrugLabel object for the uploaded label
            dl = DrugLabel(
                source=form.cleaned_data["source"],
                product_name=form.cleaned_data["product_name"],
                generic_name=form.cleaned_data["generic_name"],
                version_date=dt.datetime.now(),
                source_product_number=form.cleaned_data["product_number"],
                marketer=form.cleaned_data["marketer"],
            )
            try:
                dl.save()
            except IntegrityError:
                msg = "Unable to add the drug label. Try changing the product number."
                return my_labels_view(request, msg)

            # create the MyLabel object referencing the DrugLabel
            ml = MyLabel(
                user=request.user,
                drug_label=dl,
                name=form.cleaned_data["name"],
                file=request.FILES["file"],
            )
            ml.save()

            # process the file
            # send to load_fda_data or load_ema_data
            # --type my_label --my_label_id ml.id
            command = (
                "load_fda_data"
                if form.cleaned_data["source"] == "FDA"
                else "load_ema_data"
            )
            management.call_command(command, type="my_label", my_label_id=ml.id)

            # add to latest_drug_labels
            sql = f"INSERT INTO latest_drug_labels VALUES ({dl.id})"
            with connection.cursor() as cursor:
                cursor.execute(sql)

    return redirect(reverse("users:my_labels"))
