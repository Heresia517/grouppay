"""Config pytest globale — Fix Playwright Windows.

DOIT être à la racine du projet pour être chargé AVANT pytest-django
et pytest-playwright.
"""
import sys
import asyncio

# ═══════════════════════════════════════════════════════════════
# FIX WINDOWS : ProactorEventLoop obligatoire pour subprocess
# (sans ça, Playwright échoue avec NotImplementedError)
# ═══════════════════════════════════════════════════════════════
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print(f"[conftest] Windows ProactorEventLoop forcé")
