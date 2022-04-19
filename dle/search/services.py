from typing import List, Tuple, Dict
import logging

import bleach

from .models import SearchRequest, InvalidSearchRequest
from .search_constants import MAX_LENGTH_SEARCH_RESULT_DISPLAY, SECTION_QUERY_TEMP_TABLE_NAME, DRUG_LABEL_QUERY_TEMP_TABLE_NAME
from data.models import DrugLabel, ProductSection
from data.constants import LASTEST_DRUG_LABELS_TABLE
from django.http import QueryDict
from django.db import connection

logger = logging.getLogger(__name__)

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

def run_dl_query(search_request: SearchRequest):
    search_filter_mapping = {
        "select_agency": "source",
        "manufacturer_input": "marketer",
        "generic_name_input": "generic_name",
        "brand_name_input": "product_name",
    }
    search_request_dict = search_request._asdict()
    sql_params = {}

    sql = f"""
    CREATE TEMPORARY TABLE {DRUG_LABEL_QUERY_TEMP_TABLE_NAME} AS
    SELECT id
    FROM data_druglabel
    WHERE 1=1 
    """

    if not search_request.all_label_versions:
        # limit to most recent version
        sql += f" AND id IN (SELECT id FROM {LASTEST_DRUG_LABELS_TABLE})"

    for k, v in search_request_dict.items():
        if v and (k in search_filter_mapping):
            param_key = search_filter_mapping[k]
            sql_params[param_key] = v
            additional_filter = f" AND LOWER({param_key}) = %({param_key})s "
            sql += additional_filter

    with connection.cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {DRUG_LABEL_QUERY_TEMP_TABLE_NAME}")
        cursor.execute(sql, sql_params)

def build_match_sql(search_text: str) -> str:
    if '"' in search_text:
        mode = "BOOLEAN MODE"
    else:
        mode = "NATURAL LANGUAGE MODE"
    return f"match(section_text) AGAINST ( %(search_text)s IN {mode})"

def run_ps_query(search_request: SearchRequest):
    match_sql = build_match_sql(search_request.search_text)
    sql_params = {
        "search_text": search_request.search_text,
        "section_name": search_request.select_section,
    }
    sql = f"""
    CREATE TEMPORARY TABLE {SECTION_QUERY_TEMP_TABLE_NAME} AS
    SELECT 
        ps.id, 
        label_product_id,
        {match_sql} AS score
    FROM data_productsection as ps
    JOIN data_labelproduct as lp ON lp.id = ps.label_product_id
    JOIN data_druglabel as dl ON lp.drug_label_id = dl.id
    WHERE {match_sql}
    AND dl.id IN (
        SELECT id FROM {DRUG_LABEL_QUERY_TEMP_TABLE_NAME}
    )
    """

    if search_request.select_section:
        sql += """ AND LOWER(section_name) = %(section_name)s"""

    with connection.cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {SECTION_QUERY_TEMP_TABLE_NAME}")
        cursor.execute(sql, sql_params)

def process_search(search_request: SearchRequest) -> List[DrugLabel]:
    # first we get the list of drug_labels we want to look at
    run_dl_query(search_request)

    # then we score the section_text against the search query
    run_ps_query(search_request)

    # then we rank the scores and find the most relevant sections
    sql = f"""
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
            {SECTION_QUERY_TEMP_TABLE_NAME}
            GROUP BY
            1,
            2
        ) as cte2
        JOIN data_labelproduct AS lp ON cte2.label_product_id = lp.id
        JOIN data_productsection AS pcte ON cte2.section_id = pcte.id
        JOIN data_druglabel AS dl ON lp.drug_label_id = dl.id
        WHERE
        cte2.score_rank = 1
        ORDER BY cte2.score DESC
        LIMIT 30
        """

    logger.info(f"sql: {sql}")
    return [d for d in DrugLabel.objects.raw(sql)]


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
    section_names = ProductSection.objects.values_list(
        "section_name", flat=True
    ).distinct()
    type_ahead_mapping = {
        "manufacturers": [m.lower() for m in marketers],
        "generic_name": [g.lower() for g in generic_names],
        "brand_name": [p.lower() for p in product_names],
        "section_name": [s.lower() for s in section_names],
    }

    return type_ahead_mapping
