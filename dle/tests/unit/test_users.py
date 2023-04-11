from django.db import IntegrityError

import pytest
import requests
from pytest_django.asserts import assertTemplateUsed

from data.models import DrugLabel
from users.models import MyLabel, User

from ..utils import is_responsive_404


@pytest.mark.django_db
def test_register_user(client, http_service):
    response = client.post(
        "/users/register/",
        {
            "username": "testuser",
            "email": "testuser@gmail.com",
            "password": "testuser",
            "confirmation": "testuser",
        },
    )
    print(response)
    assert(response.status_code == 302)

@pytest.mark.django_db
def test_register_existing_user(client, http_service):
    """TODO: re-registering an existing user should fail.
    See existing user in fixture
    """
    pass

@pytest.mark.django_db
def test_login_users(client, http_service):
    """Logs in existing user from fixture
    Password in the fixture is hashed. """
    response = client.post(
        "/users/login/",
        {"username": "admin", "password": "Wtb8qbY0kH54bF"},
    )
    assert(response.status_code==302)

def test_logout_users(client, http_service):
    response = client.get("/users/logout/")
    assert(response.status_code==302)

@pytest.mark.django_db
def test_insert_my_label(client, http_service):
    test_user = User.objects.get(username="admin")
    num_entries = MyLabel.objects.count()
    dl = DrugLabel(
        source="EMA",
        product_name="Diffusia",
        generic_name="lorem ipsem",
        version_date="2022-03-15",
        source_product_number="ABC-123-DO-RE-ME",
        raw_text="Fake raw label text",
        marketer="Landau Pharma",
    )
    dl.save()
    # are labels accessible to anyone until they are linked to a MyLabel?
    ml = MyLabel(
        user=test_user,
        drug_label=dl
    )
    ml.save()
    num_new_entries = MyLabel.objects.count()
    assert num_new_entries == num_entries + 1

@pytest.mark.django_db
def user_can_load_labels_html(client, http_service):
    test_user = User.objects.get(username="admin")
    response = client.get("/users/my_labels/", {"user": test_user})
    assert response.status_code == 200
    assertTemplateUsed(response, "users/my_labels.html")

def unauthenticated_user_cannot_access_my_labels(client, http_service):
    response = client.get("/users/my_labels/")
    # TODO Check that we're actually not getting anything back, status code is only part of the story
    assert response.status_code == 302
