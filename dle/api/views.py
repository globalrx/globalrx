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
    res["status"] = status
    return JsonResponse(res)
