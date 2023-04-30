import json

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from elasticsearch_django.settings import get_client
from sentence_transformers import SentenceTransformer

from data.models import DrugLabel
from data.util import compute_section_embedding

from .apps import ApiConfig


#TODO figure out how to use CSRF in the template
@csrf_exempt
def searchkit(request: HttpRequest) -> JsonResponse:
    """Core search API which gets proxied to Elasticsearch"""
    es = get_client()
    print(request.body)
    res = es.msearch(searches=request.body)
    # res is returned as an elastic_transport.ObjectApiResponse
    return JsonResponse(dict(res))

@csrf_exempt
def vectorize(request: HttpRequest) -> JsonResponse:
    """Vectorize a search query"""
    data = json.loads(request.body)
    query = data.get("query", "")
    status = "Failed"
    res = {
        "query": query
    }
    if query:
        vector = compute_section_embedding(text=query, model=ApiConfig.pubmedbert_model)
        if len(vector) == 768:
            status = "Success"
            res["vector"] = vector
        else:
            res["vector"] = []
    else:
        res["vector"] = []
    res["status"] = status
    return JsonResponse(res)

def get_simple_query_string(query: str | None, fields: list, filters: list = [], default_operator: str = "and") -> dict:
    """Construct a simple query string query for Elasticsearch"""
    if not query:
        res = {
            "query": {
                "bool": {
                }
            }
        }
    else:
        res = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "simple_query_string": {
                                "query": query,
                                "fields": fields,
                                "default_operator": default_operator,
                            }
                        }
                    ],
                }
            }
        }
    if len(filters) > 0:
        res["query"]["bool"]["filter"] = []
        for filter in filters:
            res["query"]["bool"]["filter"].append({
                "term": {
                    filter[0]: filter[1]
                }
            })
    return res

@csrf_exempt
def search(request: HttpRequest) -> JsonResponse:
    """Wrapper endpoint for a search against Elasticsearch.
    GET requests are proxied to Elasticsearch.
    Uses BM25 scoring for now.
    """
    # Can only filter on fields indexed as keyword
    # drug_label_source is indexed directly as keyword, everything else is indexed as text with the sub-field keyword
    valid_filters = ["drug_label_generic_name", "drug_label_marketer", "drug_label_product_name", "section_name", "drug_label_source"]
    # the number of results to return
    size = request.GET.get("size", 10)
    # from is the result offset, not a page offset
    from_ = request.GET.get("from", 0)

    q = request.GET.get("q", "")
    print(f"query: {q}")
    fields = request.GET.get("fields", "*")
    fields = fields.split(",")
    filters = request.GET.get("filters", "")
    # split into a list of key value tuples
    if len(filters) > 0:
        filters = filters.split(",")
        clean_filters = []
        for filter in filters:
            pair = filter.split(":")
            if pair[0] not in valid_filters:
                return JsonResponse({
                    "error": "Invalid filter"
                })
            if pair[0] != "drug_label_source":
                pair[0] = f"{pair[0]}.keyword"
            clean_filters.append(pair)
        filters = clean_filters
    else:
        filters = []
    print(filters)

    default_operator = request.GET.get("default_operator", "AND")

    formatted_query = get_simple_query_string(query=q, fields=fields, default_operator=default_operator, filters=filters)
    print(formatted_query)

    es = get_client()
    res = es.search(
        index="productsection",
        body=formatted_query,
        fields=fields,
        from_=from_,
        size=size,
    )
    formatted_res = {
        "took": res["took"],
        "timed_out": res["timed_out"],
        "hits": {
            "total": res["hits"]["total"]["value"],
            "max_score": res["hits"]["max_score"],
        }
    }
    formatted_res["hits"]["hits"] = []
    for hit in res["hits"]["hits"]:
        fields = hit["fields"]
        del fields["text_embedding"]
        for field in fields:
            fields[field] = fields[field][0]
        formatted_hit = {
            "score": hit["_score"],
            "fields": fields
        }
        formatted_res["hits"]["hits"].append(formatted_hit)

    return JsonResponse(formatted_res)

@csrf_exempt
def search_label(request: HttpRequest) -> JsonResponse:
    """Searches Django for a DrugLabel"""
    q = request.GET.get("q", "")
    print(f"query: {q}")
    labels = DrugLabel.objects.filter(product_name__icontains=q)

    return JsonResponse({
        "labels": [dl.as_dict() for dl in labels]
    })
