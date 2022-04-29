from typing import Dict, NamedTuple, Optional
from django.http import QueryDict


"""
/search/results?search_text=blandit&select_agency=fda&manufacturer_input=gsk&marketing_category_input=&country_input=&generic_name_input=&brand_name_input=&ndc_input=
"""


class SearchRequest(NamedTuple):
    search_text: str
    select_section: str
    select_agency: Optional[str] = None
    manufacturer_input: Optional[str] = None
    marketing_category_input: Optional[str] = None
    generic_name_input: Optional[str] = None
    brand_name_input: Optional[str] = None
    ndc_input: Optional[str] = None
    all_label_versions: Optional[bool] = False

    @classmethod
    def from_search_query_dict(cls, search_query_dict: QueryDict) -> "SearchRequest":
        cls_params = [search_query_dict.get(field, "").lower() for field in cls._fields]

        return cls._make(cls_params)

    @classmethod
    def build_url_query(cls, search_request: "SearchRequest") -> str:
        search_request_dict = search_request._asdict()
        return "".join(
            [f"&{field}={search_request_dict[field]}" for field in cls._fields]
        )


class InvalidSearchRequest(Exception):
    pass
