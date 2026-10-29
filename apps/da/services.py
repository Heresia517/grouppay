"""Services de signature numerique DA."""
import hashlib
import io
import secrets

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone


def compute_document_hash(purchase_request):
    """SHA-256 du contenu d'une DA."""
    parts = [
        str(purchase_request.id),
        purchase_request.number,
        str(purchase_request.requester_id),
        str(purchase_request.total_amount),
        purchase_request.currency_code,
        purchase_request.status,
    ]
    for item in purchase_request.items.order_by("item__name"):
        parts.append(f"{item.item_id}:{item.quantity}:{item.unit_price}")

    content = "|".join(parts)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_signature_hash(document_hash, signer_id, signer_role, timestamp):
    """SHA-256 unique + nonce."""
    parts = [
        document_hash,
        str(signer_id),
        signer_role,
        timestamp.isoformat(),
        secrets.token_hex(16),
    ]
    content = "|".join(parts)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def hash_otp_code(code):
    """Hash SHA-256 d'un code OTP."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def generate_visual_signature(signer, signer_role, signed_at, signature_hash):
    """Genere une image PNG de la signature visuelle."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    W, H = 600, 200
    img = Image.new("RGB", (W, H), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (W - 1, H - 1)], outline=(37, 99, 235), width=3)
    draw.rectangle([(0, 0), (W, 45)], fill=(37, 99, 235))

    try:
        font_title = ImageFont.truetype("arial.ttf", 22)
        font_body = ImageFont.truetype("arial.ttf", 16)
        font_small = ImageFont.truetype("arial.ttf", 12)
        font_mono = ImageFont.truetype("cour.ttf", 11)
    except (OSError, IOError):
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_mono = ImageFont.load_default()

    draw.text((15, 12), "SIGNATURE ELECTRONIQUE", fill=(255, 255, 255), font=font_title)

    y = 65
    draw.text((20, y), "Signataire :", fill=(100, 116, 139), font=font_small)
    draw.text((130, y), signer.email, fill=(15, 23, 42), font=font_body)
    y += 28

    draw.text((20, y), "Role :", fill=(100, 116, 139), font=font_small)
    role_labels = {
        "SERVICE_CHIEF": "Chef de service",
        "DIRECTOR": "Directeur de direction",
        "ACHATS_DIRECTOR": "Directeur des Achats",
        "DG": "Directeur General",
    }
    draw.text((130, y), role_labels.get(signer_role, signer_role), fill=(15, 23, 42), font=font_body)
    y += 28

    draw.text((20, y), "Date :", fill=(100, 116, 139), font=font_small)
    draw.text((130, y), signed_at.strftime("%d/%m/%Y a %H:%M:%S"), fill=(15, 23, 42), font=font_body)
    y += 30

    draw.text((20, y), "Empreinte :", fill=(100, 116, 139), font=font_small)
    draw.text((130, y), signature_hash[:32] + "...", fill=(37, 99, 235), font=font_mono)

    draw.text((20, H - 25), "Verifiable sur ZionPay — Document signe",
              fill=(148, 163, 184), font=font_small)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ContentFile(buf.read(), name=f"sig-{signature_hash[:8]}.png")


def generate_verification_qr(signature_hash, base_url=None):
    """Genere un QR code PNG."""
    try:
        import qrcode
    except ImportError:
        return None

    if base_url is None:
        base_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")

    url = f"{base_url}/verify/{signature_hash}/"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ContentFile(buf.read(), name=f"qr-{signature_hash[:8]}.png")


def generate_otp_code():
    """Code numerique a 6 chiffres."""
    return "".join(str(secrets.randbelow(10)) for _ in range(6))


def send_otp_sms(user, code):
    """Envoie le code OTP par SMS."""
    from apps.notifications.sms_service import send_sms

    if not user.phone:
        return False, "Numero non renseigne"

    message = (
        f"ZionPay: votre code de signature est {code}. "
        f"Valable 10 minutes. Ne le partagez avec personne."
    )
    success = send_sms(user.phone, message)
    return success, None


def create_signature(purchase_request, signer, signer_role,
                     signature_level="PIN_OTP", comment="",
                     request=None, otp_verified=False):
    """Cree une signature numerique complete."""
    from .models import DASignature

    document_hash = compute_document_hash(purchase_request)
    now = timezone.now()
    signature_hash = compute_signature_hash(
        document_hash, signer.id, signer_role, now,
    )

    sig = DASignature(
        organization=purchase_request.organization,
        purchase_request=purchase_request,
        signer=signer,
        signer_role=signer_role,
        signature_level=signature_level,
        signature_hash=signature_hash,
        document_hash=document_hash,
        otp_verified=otp_verified,
        otp_verified_at=now if otp_verified else None,
        comment=comment,
    )

    if request:
        sig.signed_ip = _get_client_ip(request)
        sig.signed_user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    visual = generate_visual_signature(signer, signer_role, now, signature_hash)
    if visual:
        sig.visual_image.save(visual.name, visual, save=False)

    qr = generate_verification_qr(signature_hash)
    if qr:
        sig.qr_code_image.save(qr.name, qr, save=False)

    sig.save()
    return sig


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def verify_signature(signature_hash):
    """Verifie une signature par son hash."""
    from .models import DASignature

    try:
        sig = DASignature.objects.select_related(
            "signer", "purchase_request",
        ).get(signature_hash=signature_hash)
    except DASignature.DoesNotExist:
        return {"valid": False, "reason": "Signature introuvable"}

    if sig.is_revoked:
        return {
            "valid": False,
            "reason": f"Signature revoquee le {sig.revoked_at.strftime('%d/%m/%Y')}",
            "signature": sig,
        }

    current_hash = compute_document_hash(sig.purchase_request)
    integrity_ok = current_hash == sig.document_hash

    return {
        "valid": True,
        "integrity_ok": integrity_ok,
        "signature": sig,
        "signer": sig.signer,
        "document": sig.purchase_request,
    }
