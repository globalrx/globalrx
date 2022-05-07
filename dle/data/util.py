import re

def highlight_query_string(text: str, qstring: str) -> str:
    """
    Highlights query word/phrases in input text by surrouding them with <span> tags
    Args:
        text: Section raw text from db
        qstring: A query string from search result page (could be in single/doubl quotes)
    Returns:
        str: A text with the query term highlighted (put b/n <span> tags)
    """
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
    qlist += [qterm.upper() for qterm in qlist] \
           + [qterm.capitalize() for qterm in qlist] \
           + [qterm.title() for qterm in qlist]

    # get (index, "qterm") tuples in the input text
    positions = []
    for qterm in set(qlist):
        positions += [(_.start(), qterm) for _ in re.finditer(qterm, text)]

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
        output_text += f"<span style='background-color:yellow'>"
        output_text += positions[i][1]
        output_text += "</span>"
        start = end + len(positions[i][1])
        if i < length - 1:
            end = positions[i+1][0]

    output_text += text[start:len(text)]

    return output_text

def reformat_html_tags_in_raw_text(text: str) -> str:
    """
    Replaces difficult to render common tags in the raw text with better html tags.
    Args:
        text: Section raw text from db
    Returns:
        str: Section text with converted html tags
    """
    text = text.replace('<list listtype="unordered" ', '<ul ')
    text = text.replace('<list', '<ul ')
    text = text.replace('</list>', '</ul>')
    text = text.replace('<item', '<li')
    text = text.replace('</item>', '</li>')
    text = text.replace('<paragraph', '<p')
    text = text.replace('</paragraph>', '</p>')
    text = text.replace('<linkhtml', '<a')
    text = text.replace('</linkhtml>', '</a>')

    return text
