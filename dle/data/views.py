from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import DrugLabel, LabelProduct, ProductSection
from django.core.exceptions import ObjectDoesNotExist


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
        for section in product_sections:
            print(f"section_name: {section.section_name}")
    except ObjectDoesNotExist:
        product_sections = []

    # get all drug labels with the same product_name
    drug_label_versions = DrugLabel.objects.filter(product_name=drug_label.product_name).order_by('-version_date')

    context = {
        "drug_label": drug_label,
        "product_sections": product_sections,
        "drug_label_versions": drug_label_versions,
    }
    return render(request, "data/single_label.html", context)
