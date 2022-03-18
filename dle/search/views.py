from functools import reduce
from django.http import (
    HttpRequest,
    HttpResponse
)
from django.shortcuts import render
from .search_mock_utils import SEARCH_RESULTS
from . import services as SearchService

type_ahead_mapping = {
    "include_manufacturer": [
        "bayer",
        "gsk",
        "pfizer",
    ],
    "include_generic_name": [
        "hola",
        "como",
        "stas",
    ],
    "include_active_ingredients": [
        "bcaa",
        "creatine",
        "acetaminophen",
    ]
}


def index(request: HttpRequest) -> HttpResponse:
    """Landing page search view.
    """
    context = {}
    if request.htmx:
        query = request.GET
        if query:
            type_ahead = [
                type_ahead_mapping[k] for k in query.keys()
            ]
            context["type_ahead_datalist"] = reduce(lambda acc,e: acc + e, type_ahead, [])
            print(context)
    return render(request, "search/search.html", context)

def list_search_results(request: HttpRequest) -> HttpResponse:
    """Search results list view

    Args:
        request (HttpRequest): GET request with search text and multiple boolean flags.

    Returns:
        HttpResponse: Search results view with highlighted text
    """
    search_request_object = SearchService.validate_search(request.GET)
    search_results = [
        SearchService.build_search_result(result,search_request_object.search_text)
        for result in SEARCH_RESULTS
    ]
    context = {
        'search_results': search_results
    }
    return render(request, "search/search_results.html", context=context)