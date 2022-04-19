from typing import List, Tuple, Dict

import bleach

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
    if '"' in search_query:
        mode = "BOOLEAN MODE"
    else:
        mode = "NATURAL LANGUAGE MODE"
    return f"""
            match(section_text) AGAINST (
                %(search_query)s IN {mode}
            )    
           """


def build_with_clause(search_request: SearchRequest) -> str:
    select_clause = f"""
        SELECT
            label_product_id,
            id,
            {build_match_query(search_request.search_text)} AS score
        FROM
            data_productsection
        WHERE
            {build_match_query(search_request.search_text)}
    """
    if search_request.select_section:
      select_clause += """ AND LOWER(section_name) = %(section_name)s"""
  

    return "WITH cte AS (" + select_clause + ")"

def process_search(search_request: SearchRequest) -> List[DrugLabel]:
    search_filter_mapping = {
        "select_agency": "source",
        "manufacturer_input": "marketer",
        "generic_name_input": "generic_name",
        "brand_name_input": "product_name",
    }
    search_request_dict = search_request._asdict()
    with_clause = build_with_clause(search_request=search_request)
    select_sql = """
        SELECT
        dl.id,
        dl.source,
        dl.product_name,
        dl.generic_name,
        dl.version_date,
        dl.source_product_number,
        pcte.section_text as raw_text,
        dl.marketer,
        dl.link
        FROM
        (
            SELECT
            label_product_id,
            id as section_id,
            score,
            ROW_NUMBER() OVER(
                PARTITION BY label_product_id
                ORDER BY
                score DESC
            ) as score_rank
            FROM
            cte
            GROUP BY
            1,
            2
        ) as cte2
        JOIN data_labelproduct AS lp ON cte2.label_product_id = lp.id
        JOIN data_productsection AS pcte ON cte2.section_id = pcte.id
        JOIN data_druglabel AS dl ON lp.drug_label_id = dl.id
        WHERE
        cte2.score_rank = 1
        """

    sql_params = {"search_query": search_request.search_text}
    if search_request.select_section:
        sql_params["section_name"] =  search_request.select_section

    for k, v in search_request_dict.items():
        if v and k in search_filter_mapping:
            param_key = search_filter_mapping[k]
            if k == "select_section" and not v:
                continue
            sql_params[param_key] = v
            additional_filter = f"AND LOWER({param_key}) = %({param_key})s "
            select_sql += additional_filter
    
    order_limit_clause = """
        ORDER BY cte2.score DESC
        LIMIT 30
        """

    full_sql = with_clause + select_sql + order_limit_clause
    # print(full_sql % sql_params)
    return [d for d in DrugLabel.objects.raw(full_sql, params=sql_params)]


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
    tokens = text.split()
    comparison_token = set(search_term.lower().split())
    highlighted = False

    for index, token in enumerate(tokens):
        lower_token = token.lower()
        for comp in comparison_token:
            if lower_token == comp:
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
        len(search_result.raw_text),
        MAX_LENGTH_SEARCH_RESULT_DISPLAY,
    )
    # remove any html that might ruin styling
    naked_text = bleach.clean(search_result.raw_text, strip=True)

    # sliding window approach to mimic google's truncation
    for i in range(start, end, step):
        text = naked_text[i : i + step]
        highlighted_text, did_highlight = highlight_text_by_term(text, search_term)
        if did_highlight:
            return search_result, highlighted_text

    return search_result, naked_text[start:step]


def get_type_ahead_mapping() -> Dict[str, str]:
    marketers = DrugLabel.objects.values_list("marketer", flat=True).distinct()
    generic_names = DrugLabel.objects.values_list("generic_name", flat=True).distinct()
    product_names = DrugLabel.objects.values_list("product_name", flat=True).distinct()
    section_names = ProductSection.objects.values_list("section_name", flat=True).distinct()
    type_ahead_mapping = {
        "manufacturers": [m.lower() for m in marketers],
        "generic_name": [g.lower() for g in generic_names],
        "brand_name": [p.lower() for p in product_names],
        "section_name": [s.lower() for s in section_names]
    }

    return type_ahead_mapping