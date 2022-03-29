from functools import reduce
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from .search_mock_utils import SEARCH_RESULTS
from .search_constants import TYPE_AHEAD_MAPPING
from . import services as SearchService


def index(request: HttpRequest) -> HttpResponse:
    """Landing page search view."""
    context = {
        "type_ahead_manufacturer": TYPE_AHEAD_MAPPING["manufacturers"],
        "type_ahead_marketing_category": TYPE_AHEAD_MAPPING["marketing_category"],
        "type_ahead_country": TYPE_AHEAD_MAPPING["country"],
        "type_ahead_generic_name": TYPE_AHEAD_MAPPING["generic_name"],
        "type_ahead_brand_name": TYPE_AHEAD_MAPPING["brand_name"],
        "type_ahead_ndc": TYPE_AHEAD_MAPPING["ndc"],
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
    search_results = [
        SearchService.build_search_result(result, search_request_object.search_text)
        for result in SEARCH_RESULTS
    ]
    context = {"search_results": search_results}
    return render(request, "search/search_results/search_results.html", context=context)
