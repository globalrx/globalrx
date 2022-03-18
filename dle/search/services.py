from typing import Tuple
from .models import SearchRequest, InvalidSearchRequest
from .search_mock_utils import MockDrugLabel
from .search_constants import MAX_LENGTH_SEARCH_RESULT_DISPLAY

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
    comparison_token = search_term.lower()
    highlighted = False

    for index, token in enumerate(tokens):
        if token.lower() == comparison_token:
            tokens[index] = "<b>" + tokens[index] + "</b>"
            highlighted = True

    return " ".join(tokens), highlighted


def build_search_result(
    search_result: MockDrugLabel, search_term: str
) -> Tuple[MockDrugLabel, str]:
    """Returns search result objects with highlighted text

    Args:
        search_result (MockDrugLabel): A fake label that is used until we have a dataset
        search_term (str): The search text to highlight

    Returns:
        Tuple[MockDrugLabel, str]: Tuple object with the full drug label object and a truncated version of its text
    """
    start, end, step = (
        0,
        len(search_result.text),
        MAX_LENGTH_SEARCH_RESULT_DISPLAY,
    )
    # sliding window approach to mimic google's truncation
    for i in range(start, end, step):
        text = search_result.text[i : i + step]
        highlighted_text, did_highlight = highlight_text_by_term(text, search_term)
        if did_highlight:
            return search_result, highlighted_text

    return search_result, search_result.text[start:step]
