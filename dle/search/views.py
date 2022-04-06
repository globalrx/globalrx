from functools import reduce
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from .services import get_type_ahead_mapping
from . import services as SearchService
from data.models import DrugLabel


def index(request: HttpRequest) -> HttpResponse:
    """Landing page search view."""
    TYPE_AHEAD_MAPPING = get_type_ahead_mapping()
    context = {
        "type_ahead_manufacturer": TYPE_AHEAD_MAPPING["manufacturers"],
        "type_ahead_generic_name": TYPE_AHEAD_MAPPING["generic_name"],
        "type_ahead_brand_name": TYPE_AHEAD_MAPPING["brand_name"],
        "type_ahead_section_name": TYPE_AHEAD_MAPPING["section_name"],
    }

    return render(request, "search/search_landing/search_landing.html", context)


def list_search_results(request: HttpRequest) -> HttpResponse:
    """Search results list view

    Args:
        request (HttpRequest): GET request with search text and multiple boolean flags.

    Returns:
        HttpResponse: Search results view with highlighted text
    """
    search_request_object = SearchService.validate_search(request.GET)
    results = SearchService.process_search(search_request_object)
    search_results = [
        SearchService.build_search_result(result, search_request_object.search_text)
        for result in results
    ]

    context = {"search_results": search_results}
    return render(request, "search/search_results/search_results.html", context=context)

def view_drug(request: HttpRequest, drug_id: int) -> HttpResponse:
    context = {
        "drug": DrugLabel.objects.get(id=drug_id)
    }
    return render(request, "search/single_label_view/drug_view.html", context=context)