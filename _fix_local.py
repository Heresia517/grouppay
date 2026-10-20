"""Diagnostic + fix : mode desktop par defaut."""
import os, sys
from pathlib import Path

# ═══ 1. Diagnostic .env ═══
env_file = Path(".env")
print("=== DIAGNOSTIC ===")
if env_file.exists():
    content = env_file.read_text(encoding="utf-8")
    for line in content.split("\n"):
        if "DATABASE_URL" in line:
            print(f"  .env contient : {line}")
else:
    print("  .env absent")

# ═══ 2. Fix .env : commenter DATABASE_URL ═══
if env_file.exists():
    lines = content.split("\n")
    changed = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("DATABASE_URL=") and not stripped.startswith("#"):
            lines[i] = "# " + line
            changed = True
    if changed:
        env_file.write_text("\n".join(lines), encoding="utf-8")
        print("  [OK] DATABASE_URL commente dans .env")
    else:
        print("  [INFO] Pas de DATABASE_URL actif")

# ═══ 3. Fix base.py : detection IS_DESKTOP ═══
f = Path("config/settings/base.py")
src = f.read_text(encoding="utf-8")

# Detecter l'ancienne version
old_v1 = '''IS_DESKTOP = (
    getattr(__import__("sys"), "frozen", False)
    or __import__("os").environ.get("GROUPPAY_MODE") == "desktop"
)'''

new_logic = '''import os as _os
import sys as _sys

_is_frozen = getattr(_sys, "frozen", False)
_mode = _os.environ.get("GROUPPAY_MODE", "").lower()
_has_db_url = bool(_os.environ.get("DATABASE_URL", "").strip())

# Mode desktop par defaut.
# Serveur UNIQUEMENT si : frozen (exe), GROUPPAY_MODE=server, ou DATABASE_URL defini ET GROUPPAY_MODE absent
if _is_frozen:
    IS_DESKTOP = True
elif _mode == "server":
    IS_DESKTOP = False
elif _mode == "desktop":
    IS_DESKTOP = True
else:
    IS_DESKTOP = not _has_db_url'''

if old_v1 in src:
    src = src.replace(old_v1, new_logic, 1)
    f.write_text(src, encoding="utf-8")
    print("  [OK] base.py patche (v1)")
else:
    # Detecter si deja patche (v2 avec _is_frozen)
    if "_is_frozen" in src:
        # Corriger la logique existante pour favoriser desktop
        old_v2 = '''if _mode == "server" or (_mode != "desktop" and _has_db_url):
    IS_DESKTOP = False
else:
    IS_DESKTOP = True'''
        new_v2 = '''if _is_frozen:
    IS_DESKTOP = True
elif _mode == "server":
    IS_DESKTOP = False
elif _mode == "desktop":
    IS_DESKTOP = True
else:
    IS_DESKTOP = not _has_db_url'''
        if old_v2 in src:
            src = src.replace(old_v2, new_v2, 1)
            f.write_text(src, encoding="utf-8")
            print("  [OK] base.py patche (v2 corrigee)")
        else:
            print("  [INFO] base.py deja OK ou format inconnu")
    else:
        print("  [WARN] Format base.py inconnu")

# ═══ 4. Verification ═══
print()
print("=== VERIFICATION ===")
from dotenv import load_dotenv
load_dotenv(override=True)
print(f"  DATABASE_URL : {repr(os.environ.get('DATABASE_URL', ''))[:60]}")
print(f"  GROUPPAY_MODE: {repr(os.environ.get('GROUPPAY_MODE', ''))}")

_has_db_url = bool(os.environ.get("DATABASE_URL", "").strip())
if _has_db_url:
    print("  [WARN] DATABASE_URL encore actif — verifiez .env manuellement")
else:
    print("  [OK] Mode desktop actif (SQLite ~/.grouppay/grouppay.db)")
