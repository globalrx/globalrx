from datetime import date, datetime
from typing import NamedTuple, Optional
from django.db import models
from django.http import QueryDict

class MockDrugLabel(NamedTuple):
    drug_id: int
    drug_generic_name: str
    manufacturer: str
    text: str


# Create your models here.
class Drug(NamedTuple):
    id: int
    source: int
    generic_name: str
    brand_name: str
    application_num: str
    ndc: str
    unii: str
    set_id: str
    manufacturer: str
    class_name_id: int
    marketing_category: int
    country: int
    version: date
    creation_date: datetime
    owner: int


class SearchRequest(NamedTuple):
    search_text: str
    include_source: Optional[bool] = None
    include_generic_name: Optional[bool] = None
    include_brand_name: Optional[bool] = None
    include_application_num: Optional[bool] = None
    include_ndc: Optional[bool] = None
    include_unii: Optional[bool] = None
    include_set_id: Optional[bool] = None
    include_manufacturer: Optional[bool] = None
    include_class_name: Optional[bool] = None
    include_marketing_category: Optional[bool] = None
    include_country: Optional[bool] = None
    include_version: Optional[bool] = None
    include_creation_date: Optional[bool] = None
    include_owner: Optional[bool] = None

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
