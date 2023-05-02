import re

import pytest
from playwright.sync_api import Page, expect


# This is a test which should fail as we do not have an H1 tag on the page
def test_wrong_header(page: Page):
    with pytest.raises(AssertionError) as excinfo:
        page.goto("http://localhost:8000/search/")
        h1 = page.query_selector("h1")
        # We have no h1 tag on the page, so this should fail
        assert h1 == "SearchRx"

# Test that the brand exists
def test_right_header(page: Page):
    page.goto("http://localhost:8000/search/")
    title = page.query_selector(".brand")
    # print(type(title)) returns class 'playwright.sync_api._generated.ElementHandle'
    assert title.inner_text() == "SearchRx"

# Test that the navbar links work
def test_navbar(page: Page):
    page.goto("http://localhost:8000/search/")
    brand_link = page.query_selector(".brand-logo")
    brand_link.click()
    # Expects the URL to have /search/ in it
    expect(page).to_have_url(re.compile(".*search"))

    # the navbar should have 4 links with the correct text
    expect(page.locator("ul.nav > li")).to_have_text(["Home", "Visualizations", "Log in", "Register"], use_inner_text=True)

    # TODO verify the links are correct
    # links = page.locator("ul.nav > li > a")

# Test that the search bar works
def test_search_bar(page: Page):
    page.goto("http://localhost:8000/search/")
    page.get_by_placeholder("Search for text within drug labels (e.g. rash)").fill("rash")
    page.get_by_role("button", name="Search").click()

    # Expects the URL to have search and rash in it
    expect(page).to_have_url(re.compile(".*search.*rash"))

    # # TODO need to add data to database to test this
    # # Expects HTMX drug label results to be displayed
    # print(f"page url: {page.url}")
    # htmx_div = page.get_by_test_id("htmx-dl-search-results")
    # first_result = htmx_div.get_by_role("paragraph").nth(0)
    # expect(first_result).to_be_visible()

    # # at least three results should be displayed for "rash" search
    # assert htmx_div.get_by_role("paragraph").count() >= 3

    # # For all items in "rash" search, they should contain "rash" (case insensitive)
    # expect(htmx_div.get_by_role("paragraph")).to_contain_text(["rash"] * htmx_div.get_by_role("paragraph").count(), ignore_case=True)
