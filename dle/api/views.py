from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from elasticsearch_django.settings import get_client


#TODO figure out how to use CSRF in the template
@csrf_exempt
def searchkit(request: HttpRequest) -> JsonResponse:
    """Core search API which gets proxied to Elasticsearch"""
    es = get_client()
    res = es.msearch(searches=request.body)
    # res is returned as an elastic_transport.ObjectApiResponse
    return JsonResponse(dict(res))
