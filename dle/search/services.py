from typing import List, Tuple, Dict
from .models import SearchRequest, InvalidSearchRequest
from .search_constants import MAX_LENGTH_SEARCH_RESULT_DISPLAY
from data.models import DrugLabel, ProductSection
from django.http import QueryDict
from django.db.models import Count
import logging

logger = logging.getLogger(__name__)


def validate_search(request_query_params_dict: QueryDict) -> SearchRequest:
    """Validates search params and returns the search request object if valid.

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
    logger.debug(f"search_request_object: {search_request_object}")

    if search_request_object.search_text is not None:
        return search_request_object
    else:
        raise InvalidSearchRequest("Search request is malformed")


def process_search(search_request: SearchRequest) -> List[ProductSection]:
    search_filter_mapping = {
        "select_section": "section_name",
        "select_agency": "source",
        "manufacturer_input": "marketer",
        "marketing_category_input": "marketer",
        "generic_name_input": "generic_name",
        "brand_name_input": "product_name",
    }
    search_request_dict = search_request._asdict()
    sql_params = {"search_text": search_request.search_text}

    raw_sql = """
        SELECT id
        FROM data_productsection
        WHERE
            match(section_text) AGAINST (
                %(search_text)s IN NATURAL LANGUAGE MODE
            )
    """

    qs = DrugLabel.objects.all()

    #
    # for k, v in search_request_dict.items():
    #     if v and k in search_filter_mapping:
    #         param_key = search_filter_mapping[k]
    #         if k == "select_section" and not v:
    #             continue
    #         sql_params[param_key] = v
    #         additional_filter = f"AND LOWER({param_key}) = LOWER(%({param_key})s) "
    #         raw_sql += additional_filter
    # raw_sql += "LIMIT 30"  # can remove this once we're done testing
    # logger.debug(raw_sql)

    return [ps for ps in ProductSection.objects.raw(raw_sql, params=sql_params)]


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


def highlight_search_text(ps: ProductSection, search_term: str) -> str:
    """Returns highlighted text, where the search_term is found in the text

    Args:
        ps (ProductSection): The ProductSection from the DrugLabel
        search_term (str): The search text to highlight

    Returns:
        str: highlighted text
    """
    start, end, step = (
        0,
        len(ps.section_text),
        MAX_LENGTH_SEARCH_RESULT_DISPLAY,
    )
    # sliding window approach to mimic google's truncation
    for i in range(start, end, step):
        text = ps.section_text[i : i + step]
        highlighted_text, did_highlight = highlight_text_by_term(text, search_term)
        if did_highlight:
            return highlighted_text

    return ps.section_text[start:step]


def map_custom_names_to_section_names(name_list: List[str]) -> List[str]:
    SECTION_NAME_MAPPING = {
        "('contra', 'contraindications')": "contra",
        "('drive', 'effects on driving')": "drive",
        "('indications', 'indications')": "indications",
        "('interact', 'interactions')": "interact",
        "('over', 'overdose')": "over",
        "('pose', 'posology')": "pose",
        "('preg', 'pregnancy')": "preg",
        "('side', 'side effects')": "side",
        "('warn', 'warnings')": "warn",
    }
    return list(
        {
            n if n not in SECTION_NAME_MAPPING else SECTION_NAME_MAPPING[n]
            for n in name_list
        }
    )


def get_type_ahead_mapping() -> Dict[str, str]:
    values = DrugLabel.objects.values('marketer').annotate(count=Count('marketer')).order_by('-count')[:20]
    marketers = [v["marketer"] for v in values]

    values = DrugLabel.objects.values('generic_name').annotate(count=Count('generic_name')).order_by('-count')[:20]
    generic_names = [v["generic_name"] for v in values]

    values = DrugLabel.objects.values('product_name').annotate(count=Count('product_name')).order_by('-count')[:20]
    product_names = [v["product_name"] for v in values]

    values = ProductSection.objects.values('section_name').annotate(count=Count('section_name')).order_by('-count')[:20]
    section_names = [v["section_name"] for v in values]

    logger.debug([s.lower() for s in section_names])
    type_ahead_mapping = {
        "manufacturers": marketers,
        "generic_name": generic_names,
        "brand_name": product_names,
        "section_name": section_names,
    }

    return type_ahead_mapping
