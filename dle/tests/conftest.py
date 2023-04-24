import json
import os
import pathlib

from django.core.management import call_command

import pytest
import requests

from .utils import is_responsive_404


@pytest.fixture
def tests_dir():
    return pathlib.Path(__file__).resolve().parent


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    return pathlib.Path(__file__).resolve().parent / "docker-compose-tests.yml"


@pytest.fixture(scope="session")
def http_service(docker_ip, docker_services):
    """
    Ensure that Django service is up and responsive.
    """

    # `port_for` takes a container port and returns the corresponding host port
    port = docker_services.port_for("django_tests", 8000)
    url = "http://{}:{}".format(docker_ip, port)
    url404 = f"{url}/missing"
    docker_services.wait_until_responsive(
        timeout=1200.0, pause=0.1, check=lambda: is_responsive_404(url404)
    )
    return url

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'tests_user_fixture.json')
