
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

    result_text = text

    for qterm in qlist:
        length = len(qterm)
        index = 0
        output_text = ""
        subtext = result_text[0:]
        while index != -1:
            index = subtext.find(qterm)
            if index == -1:
                output_text += subtext
            else:
                output_text += subtext[0:index]
                output_text += f"<span style='background-color:yellow'>" 
                output_text += subtext[index: index + length]
                output_text += "</span>"
                subtext = subtext[index + length:]

        result_text = output_text

    return result_text


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
