from django.shortcuts import render
from django.http import HttpResponse
from .models import DrugLabel
from django.views import generic

def index(request):
    num_drug_labels = DrugLabel.objects.count()
    str = f"There are {num_drug_labels} Drug Labels in the system"
    return HttpResponse(str)

class SingleLabelView(generic.DetailView):
    model = DrugLabel
    context_object_name = 'drug_label'
    template_name = "data/single_label.html"
