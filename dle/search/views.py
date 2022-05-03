from typing import List, Set, Tuple
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.core.paginator import Paginator
from django.views.decorators.cache import cache_page
from search.models import SearchRequest
from .services import get_type_ahead_mapping
from . import services as SearchService
from data.models import DrugLabel

# NOTE comment out cache decoractors when doing development to view updates to your front-end templates.
@cache_page(60 * 20) # cache for 20 mins
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

@cache_page(60 * 20)
def list_search_results(request: HttpRequest) -> HttpResponse:
    """Search results list view
    Args:
        request (HttpRequest): GET request with search text and multiple boolean flags.
    Returns:
        HttpResponse: Search results view with highlighted text
    """
    search_request_object = SearchService.validate_search(request.GET)
    search_query_url = SearchRequest.build_url_query(search_request=search_request_object)
    results = SearchService.process_search(search_request_object, request.user)
    processed_labels: Set[int] = set()
    search_results_to_display: List[Tuple[DrugLabel, str]] = []
    for result in results:
        if result.id not in processed_labels:
            search_results_to_display.append(
                SearchService.build_search_result(
                    result, search_request_object.search_text
                )
            )
            processed_labels.add(result.id)

    TYPE_AHEAD_MAPPING = get_type_ahead_mapping()
    paginator = Paginator(search_results_to_display, 20) # show 20 results per pagination
    page_number = request.GET.get('page', '1')
    page_obj = paginator.get_page(page_number)
    context = {
        "page_obj": page_obj,
        "search_query_url": search_query_url,
        "search_request_object": search_request_object,
        "type_ahead_manufacturer": TYPE_AHEAD_MAPPING["manufacturers"],
        "type_ahead_generic_name": TYPE_AHEAD_MAPPING["generic_name"],
        "type_ahead_brand_name": TYPE_AHEAD_MAPPING["brand_name"],
        "type_ahead_section_name": TYPE_AHEAD_MAPPING["section_name"],
    }

    return render(request, "search/search_results/search_results.html", context=context)
