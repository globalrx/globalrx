from typing import List, Set, Tuple

from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import cache_page

from data.models import DrugLabel
from search.models import SearchRequest
from users.forms import SavedSearchForm
from users.models import MyLabel

from . import services as SearchService
from .services import get_type_ahead_mapping


# NOTE comment out cache decorators when doing development to view updates to your front-end templates.
def index(request: HttpRequest) -> HttpResponse:
    """Landing page search view."""
    # turn off caching for authenticated users
    if request.user and request.user.is_authenticated:
        return index_impl(request)
    return index_cached(request)


@cache_page(60 * 60)
def index_cached(request: HttpRequest) -> HttpResponse:
    return index_impl(request)


def index_impl(request: HttpRequest) -> HttpResponse:
    TYPE_AHEAD_MAPPING = get_type_ahead_mapping()
    context = {
        "type_ahead_manufacturer": TYPE_AHEAD_MAPPING["manufacturers"],
        "type_ahead_generic_name": TYPE_AHEAD_MAPPING["generic_name"],
        "type_ahead_brand_name": TYPE_AHEAD_MAPPING["brand_name"],
        "type_ahead_section_name": TYPE_AHEAD_MAPPING["section_name"],
    }

    return render(request, "search/search_landing/search_landing.html", context)


def list_search_results(request: HttpRequest) -> HttpResponse:
    if request.user and request.user.is_authenticated:
        return list_search_results_impl(request)
    return list_search_results_cached(request)


@cache_page(60 * 60)
def list_search_results_cached(request: HttpRequest) -> HttpResponse:
    return list_search_results_impl(request)


def list_search_results_impl(request: HttpRequest) -> HttpResponse:
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
                SearchService.build_search_result(result, search_request_object.search_text)
            )
            processed_labels.add(result.id)

    TYPE_AHEAD_MAPPING = get_type_ahead_mapping()
    paginator = Paginator(search_results_to_display, 20)  # show 20 results per pagination
    page_number = request.GET.get("page", "1")
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


def es_search(request: HttpRequest) -> HttpResponse:
    """Search results list view"""
    form = SavedSearchForm()
    if request.user.is_authenticated:
        my_labels = MyLabel.objects.filter(user=request.user).all()
    else:
        my_labels = []

    context = {
        "ELASTIC_HOST": reverse("api:searchkit_root"),
        "VECTORIZE_SERVICE": reverse("api:vectorize"),
        "form": form,
        "my_labels": my_labels,
    }

    return render(request, "search/elastic/search.html", context=context)
