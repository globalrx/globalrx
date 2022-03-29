from django.shortcuts import render
from django.http import HttpResponse
from .models import DrugLabel


def index(request):
    num_drug_labels = DrugLabel.objects.count()
    str = f"There are {num_drug_labels} Drug Labels in the system"
    return HttpResponse(str)
