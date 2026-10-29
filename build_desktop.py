"""Build ZionPay Desktop en exécutable Windows via PyInstaller."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ─── Env vars pour PyInstaller (Django en a besoin à l'analyse) ───
env = os.environ.copy()
env["DJANGO_SETTINGS_MODULE"] = "config.settings.base"
env["SECRET_KEY"] = "build-time-dummy-not-used-at-runtime"
env["ZIONPAY_MODE"] = "desktop"
env["PYTHONPATH"] = str(ROOT)

SEP = os.pathsep  # ';' sur Windows, ':' sur Unix

args = [
    sys.executable, "-m", "PyInstaller",
    "launcher.py",
    "--name=ZionPay",
    "--onefile",
    "--noconsole",
    "--clean",
    "--noconfirm",

    # Exclusions (allège + évite crashs libs manquantes)
    "--exclude-module=django.contrib.gis",
    "--exclude-module=matplotlib",
    "--exclude-module=numpy",
    "--exclude-module=pandas",
    "--exclude-module=tkinter",
    "--exclude-module=PIL.ImageQt",

    # Données embarquées
    f"--add-data={ROOT / 'templates'}{SEP}templates",
    f"--add-data={ROOT / 'static'}{SEP}static",
    f"--add-data={ROOT / 'config'}{SEP}config",
    f"--add-data={ROOT / 'apps'}{SEP}apps",

    # Collecte des packages Django clés
    "--collect-all=django",
    "--collect-all=daphne",
    "--collect-all=channels",
    "--collect-all=rest_framework",
    "--collect-all=django_otp",
    "--collect-all=environ",
    "--collect-all=pywebview",

    # Hidden imports critiques
    "--hidden-import=config.settings.base",
    "--hidden-import=config.urls",
    "--hidden-import=config.asgi",
    "--hidden-import=config.wsgi",
    "--hidden-import=apps.sync.apps",
    "--hidden-import=apps.core.dashboard_views",
    "--hidden-import=whitenoise",
    "--hidden-import=whitenoise.middleware",
    "--hidden-import=webview",
    "--hidden-import=webview.platforms.edgechromium",
    "--hidden-import=otp_totp",
    "--hidden-import=otp_totp.models",
]

print("→ Build PyInstaller en cours (5-8 min)...\n")
result = subprocess.run(args, cwd=ROOT, env=env)

if result.returncode == 0:
    exe = ROOT / "dist" / "ZionPay.exe"
    if exe.exists():
        print(f"\n✓ Build terminé : {exe}")
        print(f"  Taille : {exe.stat().st_size / 1024 / 1024:.1f} Mo")
    else:
        print("\n✓ Build OK (exe introuvable dans dist/)")
else:
    print(f"\n✗ Build échoué (code {result.returncode})")
    sys.exit(result.returncode)
