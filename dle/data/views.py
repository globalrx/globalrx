from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from django_htmx.middleware import HtmxDetails

from compare.util import *

from .models import DrugLabel, LabelProduct, ProductSection
from .util import *


class HtmxHttpRequest(HttpRequest):
    htmx: HtmxDetails


def index(request):
    num_drug_labels = DrugLabel.objects.count()
    str = f"There are {num_drug_labels} Drug Labels in the system"
    return HttpResponse(str)


def single_label_view(request, drug_label_id, search_text=""):
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

            # If navigating from search result to single label view
            # highlight the search text within the single label section text
            text = highlight_query_string(section.section_text, search_text)

            # convert common xml tags to html tags
            text = reformat_html_tags_in_raw_text(text)

            if drug_label.source == "EMA":
                sections_dict[section.section_name]["section_text"] = text.replace("\n", "<br>")
            else:
                sections_dict[section.section_name]["section_text"] = text

    except ObjectDoesNotExist:
        sections_dict = {}
        section_names = []

    # get all drug labels with the same product_name and marketer
    drug_label_versions = (
        DrugLabel.objects.filter(product_name=drug_label.product_name)
        .filter(marketer=drug_label.marketer)
        .order_by("version_date")
    )

    section_names.sort()

    context = {
        "drug_label": drug_label,
        "drug_label_versions": drug_label_versions,
        "section_names": section_names,
        "sections": [],
    }

    for sec_name in SECTIONS_ORDER:
        if sec_name in sections_dict.keys():
            context["sections"].append(sections_dict[sec_name])

    for key, val in sections_dict.items():
        if key not in SECTIONS_ORDER:
            context["sections"].append(val)

    return render(request, "data/single_label.html", context)


def visualizations(request):
    context = {}
    return render(request=request, template_name="data/visualizations.html", context=context)


# Putting this in data because it's simple and it returns data as HTML rather than JSON - it's not an API endpoint
@require_GET
def search_label_htmx(request: HtmxHttpRequest) -> HttpResponse:
    """Searches Django for a DrugLabel and returns an HTMX response.
    Searches against the DrugLabel.product_name or DrugLabel.generic_name fields,
    case insensitive.
    """
    if request.htmx:
        q = request.GET.get("query", "")
        if q:
            labels = DrugLabel.objects.filter(
                Q(product_name__icontains=q) | Q(generic_name__icontains=q)
            )

        else:
            print("No query string")
            labels = []
        return render(
            request=request,
            template_name="data/_label_search_results.html",
            context={"labels": labels},
        )
