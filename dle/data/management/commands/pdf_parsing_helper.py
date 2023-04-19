import re

import pdfplumber


# Function to filter invalid headers
# 1. Headers must not end in punctuation
# 2. All the dots ('.') must be from the section numbers
# 3. The word "see" must not be in the headers
# 4. "safe dose" is not a header
# 5. Shouldn't have any slash ('/')
def filter_headers(idx, headers):
    idx_valid, headers_valid = [], []
    for n in range(0, len(headers)):
        lastchar = headers[n].strip()[-1].lower()
        valid = (
            (lastchar in "qwertyuiopasdfghjklzxcvbnm()")
            and (
                len(headers[n].split())
                and headers[n].split()[0].count(".") == headers[n].strip().count(".")
            )
            and (headers[n].strip().lower().find("see") == -1)
            and ("safe dose" not in headers[n].strip().lower())
            and (headers[n].strip().lower().find(r"/") == -1)
        )
        if valid:
            idx_valid.append(idx[n])
            headers_valid.append(headers[n])
    return idx_valid, headers_valid


# function: input text, output list of section headers and content
def get_pdf_sections(text, pattern, headers_filter=True):
    idx, headers, sections = [], [], []
    for i, line in enumerate(text):
        if re.match(pattern, line):
            idx += [i]
            headers += [line.strip()]

    if headers_filter and len(headers) != 0:
        idx, headers = filter_headers(idx, headers)

    for n, h in enumerate(headers):
        if (n + 1) < len(headers):
            contents = text[idx[n] + 1 : idx[n + 1]]
        else:
            contents = text[idx[n] + 1 :]
        sections += ["\n".join(contents)]

    return headers, sections


# helper function for pdfplumber
def remove_tables(page):
    ts = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
    bboxes = [table.bbox for table in page.find_tables(table_settings=ts)]

    def not_within_bboxes(obj):
        # Check if the object is in any of the table's bbox.
        def obj_in_bbox(_bbox):
            # See https://github.com/jsvine/pdfplumber/blob/stable/pdfplumber/table.py#L404
            v_mid = (obj["top"] + obj["bottom"]) / 2
            h_mid = (obj["x0"] + obj["x1"]) / 2
            x0, top, x1, bottom = _bbox
            return (h_mid >= x0) and (h_mid < x1) and (v_mid >= top) and (v_mid < bottom)

        return not any(obj_in_bbox(__bbox) for __bbox in bboxes)

    return page.filter(not_within_bboxes)


# helper function for pdfplumber
def remove_margins(page, dpi=72, size=0.7):
    # strip 0.7 inches from top and bottom (page numbers, header text if any), A4 is 8.25 x 11.75
    # syntax is page.crop((x0, top, x1, bottom))
    w = float(page.width) / dpi
    h = float(page.height) / dpi
    return page.crop((0, (size) * dpi, w * dpi, (h - size) * dpi))


# function: input file, output text of annex 1
def read_pdf(filename, no_margins=True, no_blanks=False, no_tables=False, no_annex=True):
    text = []
    with pdfplumber.open(filename) as pdf:
        for page in pdf.pages:
            if no_margins:
                page = remove_margins(page)

            if no_tables:
                page = remove_tables(page)

            page_text = page.extract_text().split("\n")
            text += page_text

    if no_annex:
        annex_lines = [re.match(r".*ANNEX\s+I.*", line) is not None for line in text]
        annex_index = [i for i, v in enumerate(annex_lines) if v]
        text = text[annex_index[0] : annex_index[1]]

    if no_blanks:
        text = [line for line in text if not line.isspace()]

    return text
