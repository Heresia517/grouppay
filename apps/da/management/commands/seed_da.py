"""Management command : python manage.py seed_da"""
from decimal import Decimal
from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.organizations.models import Direction, Service
from apps.da.models import DACategory, DAItem


class Command(BaseCommand):
    help = "Seed les donnees de demo pour le module Demande d'Achat"

    def add_arguments(self, parser):
        parser.add_argument("--email", type=str, default="", help="Email du superuser")

    def handle(self, *args, **options):
        email = options.get("email", "")

        if email:
            user = User.objects.filter(email=email).first()
        else:
            user = User.objects.filter(is_superuser=True).first()

        if not user:
            self.stdout.write(self.style.ERROR("Aucun superuser trouve."))
            self.stdout.write("Utilisez : python manage.py seed_da --email votre@email.com")
            return

        org = user.organization
        self.stdout.write(self.style.SUCCESS(f"Seed pour : {org.name}"))

        # --- Directions ---
        daf, _ = Direction.objects.get_or_create(
            organization=org, code="DAF",
            defaults={"name": "Direction Administrative et Financiere", "display_order": 1},
        )
        dt, _ = Direction.objects.get_or_create(
            organization=org, code="DT",
            defaults={"name": "Direction Technique", "display_order": 2, "director": user},
        )
        da_dir, _ = Direction.objects.get_or_create(
            organization=org, code="DA",
            defaults={"name": "Direction des Achats", "display_order": 3, "is_achats": True, "director": user},
        )

        # --- Services ---
        svc_moyens, _ = Service.objects.get_or_create(
            organization=org, code="MOY",
            defaults={"name": "Service Moyens Generaux", "direction": daf, "chief": user},
        )
        svc_maint, _ = Service.objects.get_or_create(
            organization=org, code="MAINT",
            defaults={"name": "Service Maintenance", "direction": dt, "chief": user},
        )

        self.stdout.write(f"  {Direction.objects.filter(organization=org).count()} directions")
        self.stdout.write(f"  {Service.objects.filter(organization=org).count()} services")

        # --- Categories ---
        cat_papeterie, _ = DACategory.objects.get_or_create(
            organization=org, name="Papeterie",
            defaults={"description": "Papier, stylos, classeurs", "display_order": 1},
        )
        cat_consommables, _ = DACategory.objects.get_or_create(
            organization=org, name="Consommables informatiques",
            defaults={"description": "Cartouches, toner, cables", "display_order": 2},
        )
        cat_entretien, _ = DACategory.objects.get_or_create(
            organization=org, name="Produits d entretien",
            defaults={"description": "Produits menagers, hygiene", "display_order": 3},
        )

        # --- Articles ---
        items_data = [
            ("PAP-A4-500", "Papier A4 80g (500 feuilles)", cat_papeterie, "REAM", 3500, 50, 10),
            ("PAP-A3-500", "Papier A3 80g (500 feuilles)", cat_papeterie, "REAM", 7500, 15, 5),
            ("STY-BIC-B", "Stylos bille bleus", cat_papeterie, "PCS", 150, 200, 50),
            ("CLS-A4-B", "Classeurs A4 bleus", cat_papeterie, "PCS", 1200, 30, 10),
            ("ENV-A4-K", "Enveloppes A4 kraft", cat_papeterie, "PACK", 2500, 20, 5),
            ("CAR-HP-26A", "Cartouche HP 26A noire", cat_consommables, "PCS", 45000, 5, 3),
            ("USB-16G", "Cle USB 16 Go", cat_consommables, "PCS", 5000, 12, 5),
            ("CABLE-HDMI", "Cable HDMI 2m", cat_consommables, "PCS", 3000, 8, 5),
            ("COLLE-BAT", "Colle baton 22g", cat_entretien, "PCS", 800, 40, 15),
            ("DET-SAV", "Detergent savon 5L", cat_entretien, "L", 4500, 10, 5),
        ]

        created_items = 0
        for ref, name, cat, unit, price, stock, reorder in items_data:
            _, created = DAItem.objects.get_or_create(
                organization=org, reference=ref,
                defaults={
                    "name": name, "category": cat, "unit": unit,
                    "unit_price": Decimal(str(price)),
                    "stock_quantity": stock, "reorder_level": reorder,
                },
            )
            if created:
                created_items += 1

        self.stdout.write(f"  {DACategory.objects.filter(organization=org).count()} categories ({created_items} nouveaux articles)")
        self.stdout.write(f"  {DAItem.objects.filter(organization=org).count()} articles")

        # Marquer user comme DG + Chef + Directeur pour tester
        update_fields = []
        if not user.is_dg:
            user.is_dg = True
            update_fields.append("is_dg")
        if not user.is_service_chief:
            user.is_service_chief = True
            update_fields.append("is_service_chief")
        if not user.is_director:
            user.is_director = True
            update_fields.append("is_director")
        if not user.service:
            user.service = svc_maint
            update_fields.append("service")

        if update_fields:
            user.save(update_fields=update_fields)
            self.stdout.write(self.style.WARNING(f"  User {user.email} : DG + Chef + Directeur + service Maintenance"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Seed DA termine !"))
        self.stdout.write(f"  Acces : /da/")
        self.stdout.write(f"  Superuser : {user.email}")
