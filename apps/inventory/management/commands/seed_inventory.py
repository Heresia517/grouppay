"""Management command : python manage.py seed_inventory"""
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.inventory.models import AssetCategory, Asset


class Command(BaseCommand):
    help = "Seed donnees inventaire de demo"

    def handle(self, *args, **options):
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            self.stdout.write(self.style.ERROR("Aucun superuser"))
            return

        org = user.organization
        self.stdout.write(f"Seed inventaire pour {org.name}")

        # Categories
        categories_data = [
            ("INFO", "Informatique", 3),
            ("MOB", "Mobilier", 10),
            ("VEH", "Vehicules", 5),
            ("ELEC", "Electromenager", 5),
            ("AUTR", "Autres", 5),
        ]
        cats = {}
        for code, name, years in categories_data:
            cat, _ = AssetCategory.objects.get_or_create(
                organization=org, code=code,
                defaults={"name": name, "depreciation_years": years},
            )
            cats[code] = cat

        # Assets
        assets_data = [
            ("INFO", "Ordinateur Dell Latitude 5520", "Dell", "Latitude 5520", "SN-DELL-001", 750000, "GOOD"),
            ("INFO", "Ecran 24 pouces Samsung", "Samsung", "S24R350", "SN-SAM-001", 120000, "NEW"),
            ("INFO", "Imprimante HP LaserJet Pro", "HP", "LaserJet M404dn", "SN-HP-001", 350000, "GOOD"),
            ("INFO", "Switch Cisco 24 ports", "Cisco", "SF110-24", "SN-CISCO-001", 180000, "GOOD"),
            ("MOB", "Bureau direction", None, None, None, 250000, "GOOD"),
            ("MOB", "Chaise ergonomique", None, None, None, 95000, "NEW"),
            ("MOB", "Armoire metallique 2 portes", None, None, None, 150000, "GOOD"),
            ("VEH", "Toyota Hilux 4x4", "Toyota", "Hilux", "SN-TOY-001", 18000000, "GOOD"),
            ("ELEC", "Climatiseur Split 12000 BTU", "LG", "Dual Inverter", "SN-LG-001", 450000, "NEW"),
            ("ELEC", "Refrigerateur 400L", "Samsung", "RT40", "SN-SAM-002", 380000, "FAIR"),
        ]

        created = 0
        for cat_code, name, brand, model, serial, price, condition in assets_data:
            ref = f"INV-{cat_code}-{Asset.objects.filter(category=cats[cat_code]).count() + 1:06d}"
            asset, is_new = Asset.objects.get_or_create(
                organization=org, reference=ref,
                defaults={
                    "category": cats[cat_code],
                    "name": name,
                    "brand": brand or "",
                    "model_name": model or "",
                    "serial_number": serial or "",
                    "purchase_date": date.today() - timedelta(days=180),
                    "purchase_price": Decimal(str(price)),
                    "condition": condition,
                    "status": "AVAILABLE",
                    "location": "Magasin central",
                    "depreciation_rate": Decimal("20"),
                },
            )
            if is_new:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"OK {created} actifs crees"))
        self.stdout.write(f"  Categories : {AssetCategory.objects.filter(organization=org).count()}")
        self.stdout.write(f"  Actifs     : {Asset.objects.filter(organization=org).count()}")
        self.stdout.write(f"  Acces : /inventory/")
