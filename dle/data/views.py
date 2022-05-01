from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import DrugLabel, LabelProduct, ProductSection
from django.core.exceptions import ObjectDoesNotExist
from compare.util import *


def index(request):
    num_drug_labels = DrugLabel.objects.count()
    str = f"There are {num_drug_labels} Drug Labels in the system"
    return HttpResponse(str)


def single_label_view(request, drug_label_id):
    drug_label = get_object_or_404(DrugLabel, pk=drug_label_id)
    # for now, assume just one
    try:
        label_product = LabelProduct.objects.filter(drug_label_id=drug_label_id).get()
        product_sections = ProductSection.objects.filter(label_product_id=label_product.id).all()
        sections_dict = {}
        section_names = []
        for section in product_sections:
            section_names.append(section.section_name)
            sections_dict[section.section_name] = {"section_name": section.section_name}
            
            if drug_label.source == "EMA":
                sections_dict[section.section_name]["section_text"] = section.section_text.replace("\n", "<br>")
            else:
                sections_dict[section.section_name]["section_text"] = section.section_text

    except ObjectDoesNotExist:
        sections_dict = {}
        section_names = []

    # get all drug labels with the same product_name
    drug_label_versions = DrugLabel.objects.filter(product_name=drug_label.product_name).order_by('-version_date')
    section_names.sort()

    context = {
        "drug_label": drug_label,
        "drug_label_versions": drug_label_versions,
        "section_names": section_names,
        "sections": []
    }
    
    for sec_name in SECTIONS_ORDER:
        if sec_name in sections_dict.keys():
            context["sections"].append(sections_dict[sec_name])
    
    for key, val in sections_dict.items():
        if key not in SECTIONS_ORDER:
            context["sections"].append(val)

    return render(request, "data/single_label.html", context)
