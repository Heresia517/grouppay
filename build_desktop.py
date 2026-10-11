"""Build GroupPay Desktop en exécutable Windows via PyInstaller."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

args = [
    sys.executable, "-m", "PyInstaller",
    "launcher.py",
    "--name=GroupPay",
    "--onefile",
    "--noconsole",
    "--clean",
    f"--add-data={ROOT / 'templates'};templates",
    f"--add-data={ROOT / 'static'};static",
    f"--add-data={ROOT / 'config'};config",
    f"--add-data={ROOT / 'apps'};apps",
    "--collect-all=django",
    "--collect-all=daphne",
    "--collect-all=channels",
    "--collect-all=django_otp",
    "--collect-all=otp_totp",
    "--collect-all=rest_framework",
    "--collect-all=environ",
    "--hidden-import=config.settings.base",
    "--hidden-import=apps.sync.apps",
    "--hidden-import=webview",
    "--hidden-import=webview.platforms.edgechromium",
]

print("→ Build en cours…")
result = subprocess.run(args, cwd=ROOT)

if result.returncode == 0:
    exe = ROOT / "dist" / "GroupPay.exe"
    print(f"\n✓ Build terminé : {exe}")
    print(f"  Taille : {exe.stat().st_size / 1024 / 1024:.1f} Mo")
else:
    print("\n✗ Build échoué")
    sys.exit(result.returncode)
