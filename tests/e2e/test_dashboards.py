"""Tests E2E : un dashboard par rôle."""
import pytest
from django.urls import reverse
from apps.accounts.models import User


@pytest.mark.django_db
class TestDashboards:
    def test_dashboard_route_exists(self, client, admin_user):
        client.force_login(admin_user)
        r = client.get(reverse("dashboard"))
        assert r.status_code == 200

    def test_chef_voit_son_service(self, client, chef_user):
        client.force_login(chef_user)
        r = client.get(reverse("dashboard"))
        assert r.status_code == 200
        assert b"chef" in r.content.lower() or b"service" in r.content.lower()

    def test_membre_voit_ses_commandes(self, client, member_user):
        client.force_login(member_user)
        r = client.get(reverse("dashboard"))
        assert r.status_code == 200

    def test_livreur_voit_livraisons(self, client, courier_user):
        client.force_login(courier_user)
        r = client.get(reverse("dashboard"))
        assert r.status_code == 200
        assert b"livraison" in r.content.lower()

    def test_fournisseur_voit_produits(self, client, supplier_user):
        client.force_login(supplier_user)
        r = client.get(reverse("dashboard"))
        assert r.status_code == 200
        assert b"produit" in r.content.lower() or b"fournisseur" in r.content.lower()
