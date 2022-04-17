from typing import List, Tuple, Dict
from .models import SearchRequest, InvalidSearchRequest
from .search_constants import MAX_LENGTH_SEARCH_RESULT_DISPLAY
from data.models import DrugLabel, ProductSection

from django.http import QueryDict


def validate_search(request_query_params_dict: QueryDict) -> SearchRequest:
    """Validates search params and returns the seach request object if valid.
    Args:
        request_query_params_dict (QueryDict): Request dictionary returned from HttpRequest.GET
    Raises:
        InvalidSearchRequest
    Returns:
        SearchRequest: Validated search tuple object
    """
    search_request_object = SearchRequest.from_search_query_dict(
        request_query_params_dict
    )

    if search_request_object.search_text is not None:
        return search_request_object
    else:
        raise InvalidSearchRequest("Search request is malformed")

def build_match_query(search_query: str) -> str:
    return """
        AND match(ps.section_text) AGAINST (
                %(search_query)s IN NATURAL LANGUAGE MODE
            )    
           """


def process_search(search_request: SearchRequest) -> List[DrugLabel]:
    search_filter_mapping = {
        "select_section": "section_name",
        "select_agency": "source",
        "manufacturer_input": "marketer",
        "generic_name_input": "generic_name",
        "brand_name_input": "product_name",
    }
    search_request_dict = search_request._asdict()
    search_query = search_request.search_text.strip('"').lower()
    raw_sql = """
        SELECT
            DISTINCT dl.id,
            dl.source,
            dl.product_name,
            dl.generic_name,
            dl.version_date,
            dl.source_product_number,
            dl.marketer,
            dl.link
        FROM
            data_druglabel as dl
        JOIN data_labelproduct as lp ON dl.id = lp.drug_label_id
        JOIN data_productsection as ps ON lp.id = ps.label_product_id
        WHERE
            1=1
        """

    # exact match query
    if '"' in search_request.search_text:
        raw_sql += " AND LOWER(ps.section_text) LIKE CONCAT('%%',%(search_query)s,'%%') "
    else:
        raw_sql += build_match_query(search_query)

    sql_params = {"search_query": search_query}
    for k, v in search_request_dict.items():
        if v and k in search_filter_mapping:
            param_key = search_filter_mapping[k]
            if k == "select_section" and not v:
                continue
            sql_params[param_key] = v
            additional_filter = f"AND LOWER({param_key}) = %({param_key})s "
            raw_sql += additional_filter
    raw_sql += "LIMIT 30" #can remove this once we're done testing
    return [d for d in DrugLabel.objects.raw(raw_sql, params=sql_params)]


def highlight_text_by_term(text: str, search_term: str) -> Tuple[str, bool]:
    """Builds the highlighted texted for a given string.
    Args:
        text (str): Original text to highlight
        search_term (str): Term that should be highlighted within the text string.
    Returns:
        Tuple[str, bool]: The Highlighted Text and True if highlighting is successful
    """
    if not text:
        return "", False
    ignorable = {
        "a",
        "as",
        "and",
        "or",
        "with",
        "the",
        "be",
    }
    tokens = text.split()
    comparison_token = set(search_term.lower().split())
    highlighted = False

    for index, token in enumerate(tokens):
        lower_token = token.lower()
        for comp in comparison_token:
            if lower_token == comp and lower_token not in ignorable:
                tokens[index] = "<b>" + tokens[index] + "</b>"
                highlighted = True

    return " ".join(tokens), highlighted


def build_search_result(
    search_result: DrugLabel, search_term: str
) -> Tuple[DrugLabel, str]:
    """Returns search result objects with highlighted text
    Args:
        search_result (MockDrugLabel): A fake label that is used until we have a dataset
        search_term (str): The search text to highlight
    Returns:
        Tuple[MockDrugLabel, str]: Tuple object with the full drug label object and a truncated version of its text
    """
    start, end, step = (
        0,
        len(search_result.generic_name), #TODO CHANGE THIS WHEN FIXING HIGHLIGHTING
        MAX_LENGTH_SEARCH_RESULT_DISPLAY,
    )
    # sliding window approach to mimic google's truncation
    for i in range(start, end, step):
        text = search_result.generic_name[i : i + step]
        highlighted_text, did_highlight = highlight_text_by_term(text, search_term)
        if did_highlight:
            return search_result, highlighted_text

    return search_result, search_result.generic_name[start:step]


def get_type_ahead_mapping() -> Dict[str, str]:
    marketers = DrugLabel.objects.values_list("marketer", flat=True).distinct()
    generic_names = DrugLabel.objects.values_list("generic_name", flat=True).distinct()
    product_names = DrugLabel.objects.values_list("product_name", flat=True).distinct()
    type_ahead_mapping = {
        "manufacturers": [m.lower() for m in marketers],
        "generic_name": [g.lower() for g in generic_names],
        "brand_name": [p.lower() for p in product_names],
        "section_name": ["warnings", "pregnancy", "indications", "overdose", "interact", "side effects"], # hardcode this until figure out subsections
    }

    return type_ahead_mapping