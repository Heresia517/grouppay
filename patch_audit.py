"""Patch v2 : détecte les UniqueConstraint par lecture textuelle des models.py."""
from pathlib import Path

p = Path("audit_grouppay_v2.py")
src = p.read_text(encoding="utf-8")
original = src

# ── 1. Injecter un scanner textuel après has_any ───────────────
anchor = "has_any = lambda *names: any(n in FUNCS or n in CLASSES or n in FIELD_NAMES for n in names)"
inject = anchor + '''

# ─── Détection textuelle des contraintes ───
CONSTRAINT_TEXT = ""
for _f in FILES:
    if _f.endswith("models.py"):
        try:
            CONSTRAINT_TEXT += Path(_f).read_text(errors="ignore")
        except Exception:
            pass
'''
if "CONSTRAINT_TEXT" not in src and anchor in src:
    src = src.replace(anchor, inject, 1)
    print("✓ scanner CONSTRAINT_TEXT injecté")
else:
    print("· scanner déjà présent ou anchor introuvable")

# ── 2. Étendre la boucle RG pour RG-25 et RG-43 ────────────────
old = '''    if rg == "RG-22" and not found:'''
new = '''    # RG-25 / RG-43 : UniqueConstraint dans Meta.constraints
    if rg == "RG-25" and not found and "unique_review_per_member_product" in CONSTRAINT_TEXT:
        found = ["unique_review_per_member_product"]
    if rg == "RG-43" and not found and "unique_vote_per_member_request" in CONSTRAINT_TEXT:
        found = ["unique_vote_per_member_request"]
    if rg == "RG-22" and not found:'''
if old in src and "unique_review_per_member_product" not in src.split("CONSTRAINT_TEXT")[-1][:500]:
    src = src.replace(old, new, 1)
    print("✓ détection RG-25 + RG-43 ajoutée")
else:
    print("· détection déjà présente ou anchor introuvable")

if src != original:
    p.write_text(src, encoding="utf-8")
    print(f"\n✓ patché ({src.count(chr(10))} lignes)")
else:
    print("\n⚠️  aucune modification")

print("\n→ Relance : python audit_grouppay_v2.py")