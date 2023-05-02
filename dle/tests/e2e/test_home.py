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
    # print(htmx_div.inner_html())
    # print(htmx_div.inner_text())
    # count = htmx_div.count()
    # for i in range(count):
    #     print(i)
    #     print(htmx_div.nth(i).inner_text())
    # there should be at least 3 results which are <p> tags under htmx_results
    # for some reason .drug-label p is not working
    # htmx_results = page.locator("p") #6

    # need to wait until we get results
    # htmx_results = htmx_div.locator("p").wait_for()
    # htmx_results = htmx_div.get_by_role("paragraph")
    # htmx_results = htmx_div.get_by_role("paragraph").wait_for()
    # print(f"htmx_results.count(): {htmx_results.count()}")
    # print(htmx_results)
    # assert len(htmx_results) >= 3
    # expect(htmx_results.to_have_count(3))
    # await htmx_div.get_by_role("paragraph").nth(0).wait_for()
    expect(htmx_div.get_by_role("paragraph")).to_be_visible()
    assert htmx_div.get_by_role("paragraph").count() >= 3
    # expect(htmx_results).to_have_count(3)
    # expect(htmx_results.count()).to_be_greater_than_or_equal_to(4)

    # assert htmx_results.count() >= 3

    # Expects all results to have the word "rash" in it
    # assert "rash" in htmx_results[0].inner_text().lower()
    # expect(locator).to_contain_text()
    # for result in htmx_results.all():
    #     expect(result.to_contain_text("rash"))

    # Expects all resutls to contain the word "rash"
    # Pass a list of strings of the same length as the number of elements in the locator
    # https://playwright.dev/python/docs/api/class-locatorassertions#locator-assertions-to-contain-text
    expect(htmx_results).to_contain_text(["rash"] * htmx_results.count())
