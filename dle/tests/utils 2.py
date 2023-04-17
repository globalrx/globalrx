import requests
from requests.exceptions import ConnectionError


def is_responsive_404(url):
    """
    Hit a non existing url, expect a 404.  Used to check the service is up as a fixture.
    :param url:
    :return:
    """
    try:
        response = requests.get(url)
        if response.status_code == 404:
            return True
    except ConnectionError:
        return False
