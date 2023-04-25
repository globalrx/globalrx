import json
from typing import List, Set, Tuple

from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import cache_page

from data.models import DrugLabel
from search.models import SearchRequest
from users.forms import SavedSearchForm

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
    SEARCHKIT_SERVICE = f"{settings.API_ENDPOINT}{reverse('api:searchkit_root')}"
    VECTORIZE_SERVICE = f"{settings.API_ENDPOINT}{reverse('api:vectorize')}"
    search_query = request.GET.get('productsection[query]', '')

    print('------------------------------------------------')
    print('------------------------------------------------')
    print('------------------------------------------------')
    print('------------------------------------------------')
    print('------------------------------------------------')
    print('------------------------------------------------')
    print('------------------------------------------------')
    print('search_query', search_query)
    print('------------------------------------------------')
    print('------------------------------------------------')
    print('------------------------------------------------')
    print('------------------------------------------------')

    found_drug_labels = DrugLabel.objects.filter(product_name=search_query).all()

    print('found_drug_labels', found_drug_labels);
    print('------------------------------------------------')
    print('------------------------------------------------')
    print('------------------------------------------------')
    print('------------------------------------------------')
    print('------------------------------------------------')
    print('------------------------------------------------')



    # source = models.CharField(max_length=8, choices=SOURCES, db_index=True)
    # product_name = models.CharField(max_length=255, db_index=True)
    # generic_name = models.CharField(max_length=2048, db_index=True)
    # version_date = models.DateField(db_index=True)
    # source_product_number = models.CharField(max_length=255, db_index=True)
    # "source-specific product-id"
    # raw_text = models.TextField()
    # marketer = models.CharField(max_length=255, db_index=True)

    drug_labels = []
    for drug_label in found_drug_labels:
        drug_label_data = {
            "id": drug_label.id,
            "source": drug_label.source,
            "product_name": drug_label.product_name,
            "generic_name": drug_label.generic_name,
            "version_date": drug_label.version_date,
            "source_product_number": drug_label.source_product_number,
            "marketer": drug_label.marketer,
        }
        drug_labels.append(drug_label_data)

    print('drug_labels', drug_labels)
    print('------------------------------------------------')
    print('------------------------------------------------')
    print('------------------------------------------------')
    print('------------------------------------------------')
    print('------------------------------------------------')
    print('------------------------------------------------')


    context = {
        "SEARCHKIT_SERVICE": SEARCHKIT_SERVICE,
        "VECTORIZE_SERVICE": VECTORIZE_SERVICE,
        "form": form,
        "drug_labels": json.dumps(drug_labels, indent=4, sort_keys=True, default=str),
    }

    return render(request, "search/elastic/search.html", context=context)
