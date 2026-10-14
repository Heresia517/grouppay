"""Service d'intégration Faso Arzeka (plateforme nationale BF).

Package PyPI : fasoarzeka (non officiel)
Doc : https://my.fasoarzeka.bf  |  USSD *700#
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from fasoarzeka import (
        authenticate, initiate_payment, check_payment,
        ArzekaPayment, get_reference, format_msisdn, validate_phone_number,
    )
    FASOARZEKA_AVAILABLE = True
except ImportError:
    FASOARZEKA_AVAILABLE = False
    logger.warning("Package `fasoarzeka` non installé : pip install fasoarzeka")


class FasoArzekaClient:
    """Client haut niveau pour Faso Arzeka."""

    def __init__(self):
        cfg = settings.FASOARZEKA
        self.username = cfg["USERNAME"]
        self.password = cfg["PASSWORD"]
        self.merchant_id = cfg["MERCHANT_ID"]
        self.hash_secret = cfg["HASH_SECRET"]
        self.webhook_url = cfg["WEBHOOK_URL"]
        self.return_url = cfg["RETURN_URL"]
        self.enabled = cfg["ENABLED"] and FASOARZEKA_AVAILABLE

    def _check(self):
        if not FASOARZEKA_AVAILABLE:
            raise RuntimeError("Package `fasoarzeka` manquant. Installez : pip install fasoarzeka")
        if not self.enabled:
            raise RuntimeError("Faso Arzeka désactivé (FASOARZEKA_ENABLED=False)")

    def initier_paiement(self, montant, reference, prenom, nom, telephone, description=""):
        self._check()
        if montant < 100:
            raise ValueError("Le montant minimum est de 100 FCFA")
        mobile = format_msisdn(telephone) if validate_phone_number(telephone) else telephone
        payment_data = {
            "amount": int(montant),
            "merchant_id": self.merchant_id,
            "additional_info": {
                "first_name": prenom,
                "last_name": nom,
                "mobile": mobile,
                "paymentDescription": description or f"Paiement GroupPay {reference}",
            },
            "mapped_order_id": reference,
            "hash_secret": self.hash_secret,
            "link_for_update_status": self.webhook_url,
            "link_back_to_calling_website": self.return_url,
        }
        response = initiate_payment(payment_data)
        logger.info(f"[FasoArzeka] Paiement initié ref={reference} montant={montant} FCFA")
        return {
            "ok": True,
            "url": response.get("url") or response.get("payment_url"),
            "reference": reference,
            "mapped_order_id": response.get("mappedOrderId", reference),
        }

    def verifier_statut(self, reference):
        self._check()
        try:
            status = check_payment(reference)
            return {"ok": True, "statut": status}
        except Exception as e:
            logger.error(f"[FasoArzeka] Erreur vérif statut {reference} : {e}")
            return {"ok": False, "error": str(e)}


def get_client():
    return FasoArzekaClient()
