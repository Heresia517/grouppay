import pytest
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization

User = get_user_model()


@pytest.mark.django_db
def test_users_are_isolated_by_organization():
    """RG-05 / US-04 : un utilisateur d'une organisation ne doit
    jamais apparaître dans les données d'une autre organisation."""
    org_a = Organization.objects.create(name="Org A", slug="org-a", country_code="BF")
    org_b = Organization.objects.create(name="Org B", slug="org-b", country_code="CI")

    user_a = User.objects.create_user(email="agent@orga.com", organization=org_a, password="Test1234!")
    user_b = User.objects.create_user(email="agent@orgb.com", organization=org_b, password="Test1234!")

    # Un utilisateur de l'org A ne doit voir QUE les users de l'org A
    users_visible_from_a = User.objects.filter(organization=org_a)

    assert user_a in users_visible_from_a
    assert user_b not in users_visible_from_a
    assert users_visible_from_a.count() == 1


@pytest.mark.django_db
def test_same_email_allowed_across_different_organizations():
    """Deux organisations différentes peuvent avoir un utilisateur
    avec le même email, sans collision (contrainte composite)."""
    org_a = Organization.objects.create(name="Org A2", slug="org-a2", country_code="BF")
    org_b = Organization.objects.create(name="Org B2", slug="org-b2", country_code="CI")

    User.objects.create_user(email="meme@email.com", organization=org_a, password="Test1234!")
    User.objects.create_user(email="meme@email.com", organization=org_b, password="Test1234!")

    assert User.objects.filter(email="meme@email.com").count() == 2
