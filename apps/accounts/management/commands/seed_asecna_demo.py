"""ASECNA — Seed démo multi-pays. Introspection complète des modèles."""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.apps import apps
from decimal import Decimal
from django.utils.text import slugify


def find_model(candidates, model_name):
    for label in candidates:
        try:
            return apps.get_model(label, model_name)
        except LookupError:
            continue
    return None


def field_names(model):
    return {f.name for f in model._meta.get_fields()}


AGENTS_BF = [
    ("Abdoulaye", "Ouédraogo", "dg@asecna-bf.demo", "DG"),
    ("Fatimata", "Sawadogo", "achats@asecna-bf.demo", "DIR_ACHATS"),
    ("Boukary", "Kaboré", "dirservice@asecna-bf.demo", "DIR_SERVICE"),
    ("Aminata", "Traoré", "chef@asecna-bf.demo", "CHEF_SERVICE"),
    ("Issa", "Zongo", "rh@asecna-bf.demo", "RH"),
    ("Mariam", "Compaoré", "mariam@asecna-bf.demo", "MEMBRE"),
    ("Ousmane", "Ilboudo", "ousmane@asecna-bf.demo", "MEMBRE"),
    ("Salamata", "Bationo", "salamata@asecna-bf.demo", "MEMBRE"),
    ("Ibrahim", "Tapsoba", "ibrahim@asecna-bf.demo", "MEMBRE"),
    ("Awa", "Kindo", "awa@asecna-bf.demo", "MEMBRE"),
    ("Moussa", "Nikiéma", "moussa@asecna-bf.demo", "MEMBRE"),
    ("Ramata", "Sanou", "ramata@asecna-bf.demo", "MEMBRE"),
    ("Karim", "Ouattara", "fournisseur@asecna-bf.demo", "FOURNISSEUR"),
]

ORGS = [
    {"name": "ASECNA Burkina Faso", "slug": "asecna-bf", "country": "BF", "currency": "XOF"},
    {"name": "ASECNA Sénégal",      "slug": "asecna-sn", "country": "SN", "currency": "XOF"},
    {"name": "ASECNA Madagascar",   "slug": "asecna-mg", "country": "MG", "currency": "MGA"},
]

CATEGORIES = ["Fournitures de bureau", "Informatique", "EPI", "Mobilier",
              "Équipements aéronautiques", "Consommables", "Maintenance", "Transport"]

PRODUITS = [
    ("Ramette papier A4 80g", 0, 3500, 200),
    ("Stylo bille bleu (boîte 50)", 0, 7500, 80),
    ("Cartouche encre HP 305", 0, 22000, 40),
    ("Ordinateur portable Dell Latitude", 1, 650000, 12),
    ("Écran 24 pouces Samsung", 1, 135000, 20),
    ("Clavier + souris sans fil", 1, 25000, 45),
    ("Casque EPI antibruit", 2, 18000, 60),
    ("Gants de protection (paire)", 2, 4500, 300),
    ("Chaussures sécurité S3", 2, 32000, 50),
    ("Bureau directeur 1m60", 3, 280000, 8),
    ("Chaise ergonomique", 3, 95000, 25),
    ("Armoire métallique 2 portes", 3, 145000, 15),
    ("Balise aéronautique LED", 4, 850000, 5),
    ("Anémomètre portable", 4, 420000, 3),
    ("Jumelles 10x50", 4, 180000, 10),
    ("Papier essuie-mains (carton)", 5, 12000, 100),
    ("Savon liquide 5L", 5, 8500, 120),
    ("Gel hydroalcoolique 5L", 5, 15000, 60),
    ("Contrat maintenance clim", 6, 450000, 1),
    ("Contrat maintenance photocopieur", 6, 320000, 1),
    ("Véhicule utilitaire (location jour)", 7, 85000, 30),
    ("Carburant gasoil (litre)", 7, 815, 5000),
]


class Command(BaseCommand):
    help = "Seed démo ASECNA multi-pays (introspection)"

    def handle(self, *args, **opts):
        User = get_user_model()
        user_fields = field_names(User)
        self.stdout.write(f"  → User fields : {sorted(user_fields)}")

        Organization = find_model(["organizations", "accounts", "core", "org", "tenants"], "Organization")
        Product = find_model(["catalog", "products", "catalogue", "shop"], "Product")
        Category = find_model(["catalog", "products", "catalogue", "shop"], "Category")

        if not Organization:
            self.stdout.write(self.style.ERROR(
                f"Organization introuvable. App labels : {[a.label for a in apps.get_app_configs()]}"
            ))
            return

        org_fields = field_names(Organization)
        self.stdout.write(f"  → Organization : {Organization._meta.app_label}.{Organization.__name__}")
        if Product: self.stdout.write(f"  → Product : {Product._meta.app_label}.{Product.__name__}")
        if Category: self.stdout.write(f"  → Category : {Category._meta.app_label}.{Category.__name__}")

        # ---- Orgs ----
        orgs = []
        for o in ORGS:
            defaults = {"name": o["name"]}
            if "country" in org_fields: defaults["country"] = o["country"]
            if "currency" in org_fields: defaults["currency"] = o["currency"]
            if "modules_enabled" in org_fields: defaults["modules_enabled"] = ["mutuelle", "commandes", "bon_commande"]
            try:
                obj, created = Organization.objects.get_or_create(slug=o["slug"], defaults=defaults)
            except Exception as e:
                self.stdout.write(f"  ⚠ org {o['slug']} : {e} — fallback name")
                obj, created = Organization.objects.get_or_create(name=o["name"], defaults=defaults)
            orgs.append(obj)
            self.stdout.write(f"  {'+' if created else '='} {obj}")

        bf_org = orgs[0]

        # ---- Users ----
        for prenom, nom, email, role in AGENTS_BF:
            defaults = {}
            if "first_name" in user_fields: defaults["first_name"] = prenom
            if "last_name" in user_fields: defaults["last_name"] = nom
            if "name" in user_fields and "first_name" not in user_fields:
                defaults["name"] = f"{prenom} {nom}"
            if "organization" in user_fields: defaults["organization"] = bf_org

            u, created = User.objects.get_or_create(email=email, defaults=defaults)
            if created:
                u.set_password("Demo2024!")
                if "role" in user_fields:
                    try: u.role = role
                    except Exception: pass
                u.save()
                self.stdout.write(f"  + {prenom} {nom} ({role})")

        # ---- Catégories ----
        cats = []
        if Category:
            cat_fields = field_names(Category)
            for cname in CATEGORIES:
                defaults = {}
                if "organization" in cat_fields: defaults["organization"] = bf_org
                if "slug" in cat_fields:
                    defaults["slug"] = slugify(cname)[:50] or slugify(cname)
                try:
                    # Tente slug d'abord (unique par org), sinon name seul
                    c, _ = Category.objects.get_or_create(
                        organization=bf_org, slug=defaults.get("slug"),
                        defaults=defaults
                    ) if "slug" in cat_fields else Category.objects.get_or_create(
                        name=cname, defaults=defaults
                    )
                    cats.append(c)
                except Exception as e:
                    # Fallback : ajoute un suffixe si slug existe déjà pour une autre cat
                    try:
                        if "slug" in cat_fields:
                            base = slugify(cname)[:40]
                            for i in range(1, 20):
                                try:
                                    c, _ = Category.objects.get_or_create(
                                        organization=bf_org, slug=f"{base}-{i}",
                                        defaults={**defaults, "slug": f"{base}-{i}", "name": cname}
                                    )
                                    cats.append(c)
                                    break
                                except Exception:
                                    continue
                            else:
                                raise
                        else:
                            raise
                    except Exception as e2:
                        self.stdout.write(f"  ⚠ catégorie '{cname}' : {e2}")
                        cats.append(None)
            self.stdout.write(f"  + {sum(1 for c in cats if c)}/{len(CATEGORIES)} catégories")

        # ---- Fournisseur (obligatoire sur Product) ----
        supplier_obj = None
        Supplier = find_model(["catalog", "products", "suppliers", "shop"], "Supplier")
        if Supplier:
            sfields = field_names(Supplier)
            sdefaults = {"name": "Fournisseur Démo ASECNA"}
            if "organization" in sfields: sdefaults["organization"] = bf_org
            if "email" in sfields: sdefaults["email"] = "fournisseur@asecna-bf.demo"
            if "is_active" in sfields: sdefaults["is_active"] = True
            try:
                supplier_obj, _ = Supplier.objects.get_or_create(
                    name=sdefaults["name"], defaults=sdefaults
                )
                self.stdout.write(f"  + Fournisseur : {supplier_obj}")
            except Exception as e:
                self.stdout.write(f"  ⚠ fournisseur : {e}")
        else:
            # Pas de modèle Supplier → on prend le user FOURNISSEUR
            supplier_obj = User.objects.filter(email="fournisseur@asecna-bf.demo").first()
            if supplier_obj:
                self.stdout.write(f"  = Fournisseur (user) : {supplier_obj}")

        # ---- Produits ----
        if Product:
            prod_fields = field_names(Product)
            created_count = 0
            for nom_prod, idx, prix, stock in PRODUITS:
                defaults = {}
                for f in ("stock", "stock_quantity", "quantity", "available_stock"):
                    if f in prod_fields: defaults[f] = stock; break
                for f in ("price", "unit_price", "selling_price", "purchase_price"):
                    if f in prod_fields: defaults[f] = Decimal(str(prix)); break
                if "organization" in prod_fields: defaults["organization"] = bf_org
                if "sku" in prod_fields: defaults["sku"] = slugify(nom_prod)[:40].upper()
                if "is_active" in prod_fields: defaults["is_active"] = True
                if "category" in prod_fields and cats and cats[idx]:
                    defaults["category"] = cats[idx]
                if "supplier" in prod_fields and supplier_obj:
                    defaults["supplier"] = supplier_obj
                try:
                    _, created = Product.objects.get_or_create(name=nom_prod, defaults=defaults)
                    if created: created_count += 1
                except Exception as e:
                    self.stdout.write(f"  ⚠ produit '{nom_prod}' : {e}")
            self.stdout.write(f"  + {created_count} nouveaux produits (sur {len(PRODUITS)})")

        self.stdout.write(self.style.SUCCESS("\n✓ Seed ASECNA terminé."))
        self.stdout.write("  Login test : dg@asecna-bf.demo / Demo2024!")
