import json

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from elasticsearch_django.settings import get_client
from sentence_transformers import SentenceTransformer

from data.util import compute_section_embedding

from .apps import ApiConfig


#TODO figure out how to use CSRF in the template
@csrf_exempt
def searchkit(request: HttpRequest) -> JsonResponse:
    """Core search API which gets proxied to Elasticsearch"""
    es = get_client()
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

def get_simple_query_string(query: str, fields: list, filters: list = [], default_operator: str = "and") -> dict:
    """Construct a simple query string query for Elasticsearch"""
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
