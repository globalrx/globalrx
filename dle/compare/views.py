from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
import diff_match_patch as dmp_module
from .models import *


def index(request):
    labels_fda = DrugLabel.objects.filter(source = "FDA")[:10]
    labels_ema = DrugLabel.objects.filter(source = "EMA")[:10]
    context = {"pname_version": []}

    for drug_labels in [labels_fda, labels_ema]:
        for drug_label in drug_labels:
            context["pname_version"].append(drug_label.product_name + " : " + str(drug_label.version_date))

    return render(request, 'compare/index.html', context)

def compare_result(request):
    # get DrugLabel matching product_name and version_date
    drug_label1 = get_object_or_404(DrugLabel, product_name = request.GET['first-label'], version_date = request.GET['first-version'])
    drug_label2 = get_object_or_404(DrugLabel, product_name = request.GET['second-label'], version_date = request.GET['second-version'])

    try:
        label_product1 = LabelProduct.objects.filter(drug_label = drug_label1).first()
        dl1_sections = ProductSection.objects.filter(label_product = label_product1)
    except ObjectDoesNotExist:
        dl1_sections = []

    try:
        label_product2 = LabelProduct.objects.filter(drug_label = drug_label2).first()
        dl2_sections = ProductSection.objects.filter(label_product = label_product2)
    except ObjectDoesNotExist:
        dl2_sections = []

    # get dict in the form {section_name: [section_text1, section_text2]}
    sections_dict = {}
    for section in dl1_sections:
        sections_dict[section.section_name] = ["", ""]
    
    for section in  dl2_sections:
        sections_dict[section.section_name] = ["", ""]

    for section in dl1_sections:
        sections_dict[section.section_name][0] = section.section_text

    for section in dl2_sections:
        sections_dict[section.section_name][1] = section.section_text

    context = { 'dl1': drug_label1, 'dl2': drug_label2, "sections": []}

    dmp = dmp_module.diff_match_patch()

    # compare each section and insert data in context.sections
    for sec_name in sections_dict.keys():
        text1 = sections_dict[sec_name][0]
        text2 = sections_dict[sec_name][1]

        # compare using dmp and run cleanupSemantic
        diff = dmp.diff_main(text1, text2)
        dmp.diff_cleanupSemantic(diff)

        data = { "section_name": sec_name, 
                "section_text": diff}

        # compare if sections are exact match (maybe not necessary to highlight all sections)
        if text1 == text2:
            data["textMatches"] = "sec-match"
        else:
            data["textMatches"] = "sec-diff"
        
        context["sections"].append(data)

    return render(request, 'compare/compare_result.html', context)


# def index(request):
#     context = {'route': 'compare/index.html'}

#     dls_fda = DrugLabel.objects.filter(source = "FDA")[:6]
#     dls_ema = DrugLabel.objects.filter(source = "EMA")[:6]
#     # one_lp = LabelProduct.objects.filter(drug_label = dls[0])
#     # first_DL_sections = ProductSection.objects.filter(label_product = one_lp[0])

#     for dl in dls_fda:
#         print("--------------")
#         print(dl.source)
#         print(dl.product_name)
#         print(dl.generic_name)
#         print(dl.version_date)
#         print(dl.source_product_number)
#         print(dl.marketer)
#         print(dl.link)

#     for dl in dls_ema:
#         print("--------------")
#         print(dl.source)
#         print(dl.product_name)
#         print(dl.generic_name)
#         print(dl.version_date)
#         print(dl.source_product_number)
#         print(dl.marketer)
#         print(dl.link)
    
#     # context = {"dl_name": dls[0].product_name, "dl_version": dls[0].version_date}    
#     return render(request, 'compare/index.html')