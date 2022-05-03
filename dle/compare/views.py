from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpRequest
from django.core.exceptions import ObjectDoesNotExist
from .models import *
from .util import *
import bleach


def compare_labels(request: HttpRequest) -> HttpResponse:
    """Compare 2 or 3 different drug labels view
    Args:
        request (HttpRequest): GET request with 2 or 3 drug label ids
    Returns:
        HttpResponse: Side-by-side view of 2 or 3 drug labels for each section
    """
    drug_label1 = get_object_or_404(DrugLabel, id = request.GET['first-label'])
    drug_label2 = get_object_or_404(DrugLabel, id = request.GET['second-label'])

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

    context = { 'dl1': drug_label1, 'dl2': drug_label2}
    sections_dict = {}

    for section in dl1_sections:
        sections_dict[section.section_name] = { 
            "section_name": section.section_name, 
            "section_text1": bleach.clean(section.section_text, strip=True),
            "section_text2": "Section/subsection doesn't exist for this drug label.",
            "isCommon": "not-common-section",
        }
    
    for section in dl2_sections:
        if section.section_name in sections_dict.keys():
            sections_dict[section.section_name]["section_text2"] = bleach.clean(section.section_text, strip=True)
            sections_dict[section.section_name]["isCommon"] = "common-section"
        else:
            sections_dict[section.section_name] = { 
                "section_name": section.section_name,
                "section_text1": "Section/subsection doesn't exist for this drug label.",
                "section_text2": bleach.clean(section.section_text, strip=True),
                "isCommon": "not-common-section",
            }

    if 'third-label' in request.GET:
        print("third-label requested")
        drug_label3 = get_object_or_404(DrugLabel, id = request.GET['third-label'])
        try:
            label_product3 = LabelProduct.objects.filter(drug_label = drug_label3).first()
            dl3_sections = ProductSection.objects.filter(label_product = label_product3)
            context['dl3'] = drug_label3

            for section_name in sections_dict.keys():
                sections_dict[section_name]["section_text3"] = "Section/subsection doesn't exist for this drug label."

            for section in dl3_sections:
                if section.section_name in sections_dict.keys():
                    sections_dict[section.section_name]["section_text3"] = bleach.clean(section.section_text, strip=True)
                    sections_dict[section.section_name]["isCommon"] = "common-section"
                else:
                    sections_dict[section.section_name] = { 
                        "section_name": section.section_name,
                        "section_text1": "Section/subsection doesn't exist for this drug label.",
                        "section_text2": "Section/subsection doesn't exist for this drug label.",
                        "section_text3": bleach.clean(section.section_text, strip=True),
                        "isCommon": "not-common-section",
                    }

        except ObjectDoesNotExist:
            dl3_sections = []

    section_names_list = list(sections_dict.keys())
    section_names_list.sort()
    context["section_names"] = section_names_list
    context["sections"] = []

    for sec_name in SECTIONS_ORDER:
        if sec_name in sections_dict.keys():
            context["sections"].append(sections_dict[sec_name])
    
    for key, val in sections_dict.items():
        if key not in SECTIONS_ORDER:
            context["sections"].append(val)

    return render(request, 'compare/compare_labels.html', context)


def compare_versions(request):
    """Compare 2 versions of the same drug label
    Args:
        request (HttpRequest): GET request with 2 drug label ids
    Returns:
        HttpResponse: Side-by-side view diff view of 2 labels
    """
    # get DrugLabel matching product_name and version_date
    drug_label1 = get_object_or_404(DrugLabel, id = request.GET['first-label'])
    drug_label2 = get_object_or_404(DrugLabel, id = request.GET['second-label'])

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

    context = { 'dl1': drug_label1, 'dl2': drug_label2}
    sections_dict = {}

    for section in dl1_sections:
        sections_dict[section.section_name] = { 
            "section_name": section.section_name, 
            "section_text1": section.section_text,
            "section_text2": "Section/subsection doesn't exist for this drug label.",
            }
    
    for section in dl2_sections:
        if section.section_name in sections_dict.keys():
            sections_dict[section.section_name]["section_text2"] = section.section_text
        else:
            sections_dict[section.section_name] = { 
                "section_name": section.section_name,
                "section_text1": "Section/subsection doesn't exist for this drug label.",
                "section_text2": section.section_text,
            }

    # compare each section and insert data in context.sections
    for sec_name in sections_dict.keys():
        text1 = bleach.clean(sections_dict[sec_name]["section_text1"], strip=True)
        text2 = bleach.clean(sections_dict[sec_name]["section_text2"], strip=True)

        diff1, diff2 = get_diff_for_diff_versions(text1, text2)
        sections_dict[sec_name]["section_text1"] = diff1
        sections_dict[sec_name]["section_text2"] = diff2

        # compare if sections are exact match (maybe not necessary to highlight all sections)
        if text1 == text2:
            sections_dict[sec_name]["textMatches"] = "matching-section"
        else:
            sections_dict[sec_name]["textMatches"] = "diff-section"

    section_names_list = list(sections_dict.keys())
    section_names_list.sort()
    context["section_names"] = section_names_list
    context["sections"] = []
    
    for sec_name in SECTIONS_ORDER:
        if sec_name in sections_dict.keys():
            context["sections"].append(sections_dict[sec_name])
    
    for key, val in sections_dict.items():
        if key not in SECTIONS_ORDER:
            context["sections"].append(val)

    return render(request, 'compare/compare_versions.html', context)
