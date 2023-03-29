# from django.shortcuts import render
import json

from django.http import HttpRequest, JsonResponse


# Create your views here.

def searchkit(request: HttpRequest) -> JsonResponse:
    """Core search API which gets proxied to Elasticsearch"""
    res = {
        "test": "success"
    }
    return JsonResponse(res)
