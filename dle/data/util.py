# import json
import datetime
import math
import re
from string import Formatter

import dateparser
import numpy as np
from dateparser.search import search_dates

from data.models import DrugLabel


def highlight_query_string(text: str, qstring: str) -> str:
    """
    Highlights query word/phrases in input text by surrouding them with <span> tags
    Args:
        text: Section raw text from db
        qstring: A query string from search result page (could be in single/doubl quotes)
    Returns:
        str: A text with the query term highlighted (put b/n <span> tags)
    """
    text_lower = text.lower()

    # if qstring is empty, return text as is
    if qstring == "":
        return text

    # if qstring in double quotes, find & highligh full query str
    if qstring.startswith('"') and qstring.endswith('"'):
        qlist = [qstring[1:-1]]

    # if qstring in single quotes, find & highligh full query str
    elif qstring.startswith("'") and qstring.endswith("'"):
        qlist = [qstring[1:-1]]

    # else highlight each word in the query str, separatly
    else:
        qlist = qstring.split()

    # include upper, title, capitalized cases of the query strings
    qlist += (
        [qterm.upper() for qterm in qlist]
        + [qterm.capitalize() for qterm in qlist]
        + [qterm.title() for qterm in qlist]
    )

    # get (index, "qterm") tuples in the input text
    positions = []
    for qterm in set(qlist):
        positions += [(_.start(), qterm) for _ in re.finditer(qterm, text_lower)]

    if positions == []:
        return text

    positions.sort()
    # iterate through positions and insert <span> tags in text
    output_text = ""
    length = len(positions)
    start = 0
    end = positions[0][0]

    for i in range(length):
        output_text += text[start:end]
        output_text += "<span style='background-color:yellow'>"
        output_text += positions[i][1]
        output_text += "</span>"
        start = end + len(positions[i][1])
        if i < length - 1:
            end = positions[i + 1][0]

    output_text += text[start : len(text)]

    return output_text


def reformat_html_tags_in_raw_text(text: str) -> str:
    """
    Replaces difficult to render common tags in the raw text with better html tags.
    Args:
        text: Section raw text from db
    Returns:
        str: Section text with converted html tags
    """
    text = text.replace('<list listtype="unordered" ', "<ul ")
    text = text.replace("<list", "<ul ")
    text = text.replace("</list>", "</ul>")
    text = text.replace("<item", "<li")
    text = text.replace("</item>", "</li>")
    text = text.replace("<paragraph", "<p")
    text = text.replace("</paragraph>", "</p>")
    text = text.replace("<linkhtml", "<a")
    text = text.replace("</linkhtml>", "</a>")

    return text


def magnitude(vector):
    """Compute the magnitude of a vector so we can normalize to unit length"""
    # See: https://github.com/elastic/elasticsearch/blob/main/docs/reference/mapping/types/dense-vector.asciidoc
    return math.sqrt(sum(pow(element, 2) for element in vector))


def compute_section_embedding(text: str, model, word_count=256, normalize=True) -> list[float]:
    n_segments = 1 + len(text.split()) // word_count
    vecs = np.zeros((n_segments, 768))
    for i in range(n_segments):
        segment = text.split()[(i) * word_count : (i + 1) * word_count]
        vecs[i, :] = model.encode(" ".join(segment))
    avg_vec = np.mean(vecs, axis=0)
    if not normalize:
        return avg_vec
    else:
        m = magnitude(avg_vec)
        # return the unit length vector instead
        return [x / m for x in avg_vec]


def convert_date_string(date_string: str) -> datetime.datetime | None:
    # for date_format in ("%d %B %Y", "%d %b %Y", "%d/%m/%Y"):
    #     try:
    #         dt_obj = datetime.datetime.strptime(date_string, date_format)
    #         converted_string = dt_obj.strftime("%Y-%m-%d")
    #         # TODO should we be returning a datetime object rather than string?
    #         return converted_string
    #     except ValueError:
    #         pass
    # return ""
    parsed = dateparser.parse(date_string)
    if parsed:
        return parsed
    else:
        parsed = search_dates(date_string)
        # single hit
        if parsed and len(parsed) == 1:
            return parsed[0][1]
        # multiple or no hits, return nothing
    return None


def check_recently_updated(dl: DrugLabel, skip_timeframe: datetime.timedelta) -> bool:
    """Checks to see if a label has been updated within a timeframe
    dl: the DrugLabel to compare
    skip_timeframe: a datetime.timedelta object
    """
    # create a timedelta of how long ago a label was updated
    last_updated_ago = datetime.datetime.now(datetime.timezone.utc) - dl.updated_at
    # return if it is less than the skip_timeframe
    return last_updated_ago < skip_timeframe


# Credit to MarredCheese: https://stackoverflow.com/questions/538666/format-timedelta-to-string
def strfdelta(tdelta, fmt="{D:02}d {H:02}h {M:02}m {S:02}s", inputtype="timedelta"):
    """Convert a datetime.timedelta object or a regular number to a custom-
    formatted string, just like the stftime() method does for datetime.datetime
    objects.

    The fmt argument allows custom formatting to be specified.  Fields can
    include seconds, minutes, hours, days, and weeks.  Each field is optional.

    Some examples:
        '{D:02}d {H:02}h {M:02}m {S:02}s' --> '05d 08h 04m 02s' (default)
        '{W}w {D}d {H}:{M:02}:{S:02}'     --> '4w 5d 8:04:02'
        '{D:2}d {H:2}:{M:02}:{S:02}'      --> ' 5d  8:04:02'
        '{H}h {S}s'                       --> '72h 800s'

    The inputtype argument allows tdelta to be a regular number instead of the
    default, which is a datetime.timedelta object.  Valid inputtype strings:
        's', 'seconds',
        'm', 'minutes',
        'h', 'hours',
        'd', 'days',
        'w', 'weeks'
    """

    # Convert tdelta to integer seconds.
    if inputtype == "timedelta":
        remainder = int(tdelta.total_seconds())
    elif inputtype in ["s", "seconds"]:
        remainder = int(tdelta)
    elif inputtype in ["m", "minutes"]:
        remainder = int(tdelta) * 60
    elif inputtype in ["h", "hours"]:
        remainder = int(tdelta) * 3600
    elif inputtype in ["d", "days"]:
        remainder = int(tdelta) * 86400
    elif inputtype in ["w", "weeks"]:
        remainder = int(tdelta) * 604800

    f = Formatter()
    desired_fields = [field_tuple[1] for field_tuple in f.parse(fmt)]
    possible_fields = ("W", "D", "H", "M", "S")
    constants = {"W": 604800, "D": 86400, "H": 3600, "M": 60, "S": 1}
    values = {}
    for field in possible_fields:
        if field in desired_fields and field in constants:
            values[field], remainder = divmod(remainder, constants[field])
    return f.format(fmt, **values)


class PDFParseException(Exception):
    """Exception raised for errors parsing PDFs."""


# TODO move all vectorization functions here
# TODO create a script that can be called outside of Docker to vectorize Django data
# It should be able to vectorize all data in the database, or a subset of it
# It should be able to connect to Django to update the database with the new vectors
