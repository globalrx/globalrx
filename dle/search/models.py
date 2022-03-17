from typing import NamedTuple, Optional
from django.db import models
from django.http import QueryDict


# Create your models here.
class MockLabel(NamedTuple):
    manufacturer: str
    name: str
    label_text: str


class SearchRequest(NamedTuple):
    search_text: str
    include_name: Optional[bool] = None
    include_manufacturer: Optional[bool] = None
    include_active_ingredients: Optional[bool] = None

    @classmethod
    def from_search_query_dict(cls, search_query_dict: QueryDict) -> "SearchRequest":
        cls_params = [
            search_query_dict.get(field)
            if field not in cls._field_defaults
            else search_query_dict.get(field, False) == "true"
            for field in cls._fields
        ]

        return cls._make(cls_params)


class InvalidSearchRequest(Exception):
    pass
