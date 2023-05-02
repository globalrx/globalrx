import re

import playwright
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

    # the navbar should have 4 links
    # TODO switch to use a locator, query selector is deprecated: https://playwright.dev/python/docs/locators
    navbar_links = page.query_selector_all(".nav-link")
    assert len(navbar_links) == 4

    # TODO use https://playwright.dev/python/docs/locators#assert-all-text-in-a-list to check all text in the navbar list

    # The first navbar link should be "Home" and link to /search/
    assert navbar_links[0].inner_text() == "Home"
    assert navbar_links[0].get_attribute("href") == "/search/"

    # The second navbar link should be "Visualizations" and link to /data/visualizations
    assert navbar_links[1].inner_text() == "Visualizations"
    assert navbar_links[1].get_attribute("href") == "/data/visualizations"

    # The third navbar link should be "Log In" and link to "/users/login"
    assert navbar_links[2].inner_text() == "Log in"
    assert navbar_links[2].get_attribute("href") == "/users/login/"

    # The fourth navbar link should be "Register" and link to "/users/register"
    assert navbar_links[3].inner_text() == "Register"
    assert navbar_links[3].get_attribute("href") == "/users/register/"

# Test that the search bar works
def test_search_bar(page: Page):
    page.goto("http://localhost:8000/search/")
    page.get_by_placeholder("Search for text within drug labels (e.g. rash)").fill("rash")
    page.get_by_role("button", name="Search").click()

    # Expects the URL to have search and rash in it
    expect(page).to_have_url(re.compile(".*search.*rash"))

    # Expects HTMX drug label results to be displayed
    print(f"page url: {page.url}")
    # TODO switch to use a test_id or other selector https://playwright.dev/python/docs/other-locators#id-data-testid-data-test-id-data-test-selectors
    htmx_div = page.get_by_test_id("htmx-dl-search-results")
    first_result = htmx_div.get_by_role("paragraph").nth(0)
    expect(first_result).to_be_visible()

    # at least three results should be displayed for "rash" search
    assert htmx_div.get_by_role("paragraph").count() >= 3

    # For all items in "rash" search, they should contain "rash" (case insensitive)
    expect(htmx_div.get_by_role("paragraph")).to_contain_text(["rash"] * htmx_div.get_by_role("paragraph").count(), ignore_case=True)
