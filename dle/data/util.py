# import json
import math
import re

import numpy as np


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
