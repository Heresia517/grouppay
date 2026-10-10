"""Management command : python manage.py seed_users"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.organizations.models import Organization, Direction, Service


USERS = [
    {"email": "admin@sonabel-demo.com", "password": "admin123",
     "first_name": "Ibrahim", "last_name": "KONE", "role": "ADMIN",
     "internal_id": "DG-001", "phone": "+22670000001",
     "is_staff": True, "is_superuser": True, "is_dg": True,
     "desc": "Directeur General (acces total)"},

    {"email": "rh@sonabel-demo.com", "password": "rh123",
     "first_name": "Aminata", "last_name": "TRAORE", "role": "GESTIONNAIRE",
     "internal_id": "RH-001", "phone": "+22670000002",
     "is_staff": True,
     "desc": "Responsable RH"},

    {"email": "chef.maint@sonabel-demo.com", "password": "chef123",
     "first_name": "Karim", "last_name": "OUEDRAOGO", "role": "MEMBRE",
     "internal_id": "MAINT-001", "phone": "+22670000003",
     "is_service_chief": True, "service_code": "MAINT",
     "desc": "Chef Service Maintenance"},

    {"email": "dir.tech@sonabel-demo.com", "password": "dir123",
     "first_name": "Aicha", "last_name": "SAWADOGO", "role": "GESTIONNAIRE",
     "internal_id": "DT-001", "phone": "+22670000004",
     "is_director": True, "direction_code": "DT",
     "desc": "Directrice Technique"},

    {"email": "achats@sonabel-demo.com", "password": "achats123",
     "first_name": "Salif", "last_name": "TRAORE", "role": "GESTIONNAIRE",
     "internal_id": "ACH-001", "phone": "+22670000005",
     "is_director": True, "direction_code": "DA",
     "desc": "Directeur des Achats"},

    {"email": "membre1@sonabel-demo.com", "password": "membre123",
     "first_name": "Jean", "last_name": "DUPONT", "role": "MEMBRE",
     "internal_id": "MAINT-002", "phone": "+22670000006",
     "service_code": "MAINT",
     "desc": "Membre simple"},

    {"email": "membre2@sonabel-demo.com", "password": "membre123",
     "first_name": "Marie", "last_name": "KONE", "role": "MEMBRE",
     "internal_id": "MOY-001", "phone": "+22670000007",
     "service_code": "MOY",
     "desc": "Membre Moyens Generaux"},

    {"email": "membre3@sonabel-demo.com", "password": "membre123",
     "first_name": "Paul", "last_name": "SAWADOGO", "role": "MEMBRE",
     "internal_id": "MOY-002", "phone": "+22670000008",
     "service_code": "MOY",
     "desc": "Membre Moyens Generaux"},

    {"email": "fournisseur1@sonabel-demo.com", "password": "fourn123",
     "first_name": "SARL", "last_name": "EIM ELECTRO", "role": "FOURNISSEUR",
     "internal_id": "FOURN-001", "phone": "+22670000009",
     "desc": "Fournisseur electromenager"},

    {"email": "fournisseur2@sonabel-demo.com", "password": "fourn123",
     "first_name": "ETS", "last_name": "BURKINA FOURNITURES", "role": "FOURNISSEUR",
     "internal_id": "FOURN-002", "phone": "+22670000010",
     "desc": "Fournisseur fournitures"},

    {"email": "livreur1@sonabel-demo.com", "password": "livreur123",
     "first_name": "Boukary", "last_name": "ZONGO", "role": "LIVREUR",
     "internal_id": "LIV-001", "phone": "+22670000011",
     "desc": "Livreur 1"},

    {"email": "livreur2@sonabel-demo.com", "password": "livreur123",
     "first_name": "Issouf", "last_name": "KABORE", "role": "LIVREUR",
     "internal_id": "LIV-002", "phone": "+22670000012",
     "desc": "Livreur 2"},
]


class Command(BaseCommand):
    help = "Cree tous les utilisateurs de test"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        reset = options.get("reset", False)
        org = Organization.objects.first()

        if not org:
            self.stdout.write(self.style.ERROR("Aucune organisation. Lance seed_da d'abord."))
            return

        self.stdout.write(self.style.SUCCESS(f"Organisation : {org.name}"))
        self.stdout.write("")

        directions = {d.code: d for d in Direction.objects.filter(organization=org)}
        services = {s.code: s for s in Service.objects.filter(organization=org)}
        self.stdout.write(f"  {len(directions)} directions : {', '.join(directions.keys())}")
        self.stdout.write(f"  {len(services)} services : {', '.join(services.keys())}")
        self.stdout.write("")

        created = 0
        updated = 0

        for data in USERS:
            email = data["email"]
            if reset:
                User.objects.filter(email=email, organization=org).delete()

            user = User.objects.filter(email=email, organization=org).first()
            is_new = user is None
            if is_new:
                user = User(email=email, organization=org)

            user.first_name = data.get("first_name", "")
            user.last_name = data.get("last_name", "")
            user.role = data["role"]
            user.internal_id = data.get("internal_id", "")
            user.phone = data.get("phone", "")
            user.is_active = True
            user.is_staff = data.get("is_staff", False)
            user.is_superuser = data.get("is_superuser", False)
            user.is_dg = data.get("is_dg", False)
            user.is_director = data.get("is_director", False)
            user.is_service_chief = data.get("is_service_chief", False)

            if "service_code" in data and data["service_code"] in services:
                user.service = services[data["service_code"]]

            user.set_password(data["password"])
            user.save()

            if is_new:
                created += 1
                marker = "NEW"
            else:
                updated += 1
                marker = "UPD"

            extras = []
            if user.is_superuser: extras.append("SUPER")
            if user.is_dg: extras.append("DG")
            if user.is_director: extras.append("DIR")
            if user.is_service_chief: extras.append("CHEF")
            if user.is_staff: extras.append("STAFF")
            extras_str = f" [{','.join(extras)}]" if extras else ""

            self.stdout.write(f"  {marker:<4} {email:<42} {data['role']:<14}{extras_str}")

        # Rattachements
        self.stdout.write("")
        self.stdout.write("Rattachements...")

        dt = User.objects.filter(email="dir.tech@sonabel-demo.com", organization=org).first()
        if dt and "DT" in directions:
            directions["DT"].director = dt
            directions["DT"].save()
            self.stdout.write(f"  DT.director -> {dt.email}")

        ach = User.objects.filter(email="achats@sonabel-demo.com", organization=org).first()
        if ach and "DA" in directions:
            directions["DA"].director = ach
            directions["DA"].save()
            self.stdout.write(f"  DA.director -> {ach.email}")

        chef = User.objects.filter(email="chef.maint@sonabel-demo.com", organization=org).first()
        if chef and "MAINT" in services:
            services["MAINT"].chief = chef
            services["MAINT"].save()
            self.stdout.write(f"  MAINT.chief -> {chef.email}")

        # Resume
        self.stdout.write("")
        self.stdout.write("=" * 72)
        self.stdout.write(self.style.SUCCESS(f"  RESUME : {created} crees, {updated} mis a jour"))
        self.stdout.write("=" * 72)
        self.stdout.write("")

        credentials = [
            ("Admin / DG", "admin@sonabel-demo.com", "admin123"),
            ("RH", "rh@sonabel-demo.com", "rh123"),
            ("Chef Maintenance", "chef.maint@sonabel-demo.com", "chef123"),
            ("Directrice Technique", "dir.tech@sonabel-demo.com", "dir123"),
            ("Directeur Achats", "achats@sonabel-demo.com", "achats123"),
            ("Membre 1", "membre1@sonabel-demo.com", "membre123"),
            ("Membre 2", "membre2@sonabel-demo.com", "membre123"),
            ("Membre 3", "membre3@sonabel-demo.com", "membre123"),
            ("Fournisseur 1", "fournisseur1@sonabel-demo.com", "fourn123"),
            ("Fournisseur 2", "fournisseur2@sonabel-demo.com", "fourn123"),
            ("Livreur 1", "livreur1@sonabel-demo.com", "livreur123"),
            ("Livreur 2", "livreur2@sonabel-demo.com", "livreur123"),
        ]

        self.stdout.write("CREDENTIELS DE TEST")
        self.stdout.write("")
        for role, email, password in credentials:
            self.stdout.write(f"  {role:<22} {email:<42} {password}")
        self.stdout.write("")
