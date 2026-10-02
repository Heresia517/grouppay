#!/usr/bin/env python
"""Audit GroupPay vs PRD — v3 (AST + aliases + double app path)"""
import os, sys, ast
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
try:
    import django; django.setup()
except Exception as e:
    print(f"✗ Django: {e}"); sys.exit(1)
from django.apps import apps

# Scan AST
FUNCS, FILES = set(), set()
for p in Path('.').rglob('*.py'):
    s = str(p).replace('\\','/')
    if any(x in s for x in ['/venv/','/__pycache__/','/migrations/','/.kilo/','audit_grouppay']): continue
    FILES.add(s)
    try:
        for n in ast.walk(ast.parse(p.read_text(encoding='utf-8'))):
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)): FUNCS.add(n.name)
    except Exception: pass
has_func = lambda n: n in FUNCS

ALIASES = {'password_hash':['password'],'member':['member','user'],'actor':['actor','user'],
           'recipient':['recipient','user'],'file_path':['file','file_path'],
           'signature_image_url':['signature_image'],'photo_proof_url':['delivery_photo'],
           'primary_color':['color_primary']}
def has_field(m,f):
    n = {x.name for x in m._meta.get_fields()}
    return any(a in n for a in ALIASES.get(f,[f]))

PRD = {
    ('organizations','Organization'):['name','slug','country_code','currency_code','status','primary_color','max_users'],
    ('accounts','User'):['email','organization','role','internal_id'],
    ('catalog','Category'):['organization','parent','name','slug','is_active'],
    ('catalog','Product'):['organization','category','supplier','name','price','stock_quantity','is_active','reorder_level','max_per_member'],
    ('catalog','ProductVariant'):['product','sku','price','stock_quantity'],
    ('orders','Cart'):['user','status'],
    ('orders','CartItem'):['cart','product','quantity'],
    ('orders','Order'):['organization','order_number','member','status','delivery_address','total_amount'],
    ('orders','OrderItem'):['order','product','quantity','unit_price'],
    ('orders','OrderStatusHistory'):['order','from_status','to_status','actor'],
    ('deductions','DeductionTransmission'):['organization','order','reference','status','member_email','amount'],
    ('deductions','DeductionExportBatch'):['organization','period_start','period_end','row_count','status'],
    ('deliveries','Delivery'):['order','courier','status','attempts'],
    ('deliveries','DeliveryNoteDocument'):['delivery','file_path'],
    ('documents','PurchaseOrderDocument'):['order','file_path'],
    ('notifications','Notification'):['organization','recipient','channel','title'],
}

print("\n=== MODÈLES ===")
ok_m = part_m = miss_m = 0
for (app,name),fields in PRD.items():
    m = None
    for a in [app,'apps.'+app]:
        try: m = apps.get_model(a,name); break
        except LookupError: pass
    if m is None: print(f"  ✗ {app}.{name}"); miss_m += 1; continue
    missing = [f for f in fields if not has_field(m,f)]
    if not missing: print(f"  ✓ {app}.{name}"); ok_m += 1
    else: print(f"  ⚠ {app}.{name} manque: {','.join(missing)}"); part_m += 1
print(f"  → {ok_m} OK / {part_m} partiels / {miss_m} manquants")

RG = {
    'RG-01':['create_order_from_cart'],'RG-02':['create_order_from_cart'],
    'RG-03':['validate_order'],'RG-04':['reject_order'],
    'RG-05':['TenantModel'],'RG-06':['IsRH','IsAdmin','IsRHOrAdmin'],
    'RG-07':['reject_order'],'RG-08':['check_max_per_member'],
    'RG-09':['cleanup_expired_carts'],'RG-10':['validate_order'],
    'RG-11':['expires_at'],'RG-12':['generate_export_batch'],
    'RG-13':['generate_purchase_order_pdf'],'RG-14':['generate_export_batch'],
    'RG-15':['confirm_deduction'],'RG-16':['create_delivery_for_order'],
    'RG-17':['assign_courier'],'RG-18':['mark_delivered'],
    'RG-19':['mark_delivered'],'RG-20':['attempt_delivery'],
    'RG-21':['check_low_stock'],'RG-22':['CheckConstraint'],
    'RG-23':['decrement_stock','ProductVariant'],
}

print("\n=== RÈGLES MÉTIER ===")
rg_ok = 0
for rg, proofs in RG.items():
    found = [p for p in proofs if has_func(p)]
    if rg == 'RG-22' and not found:
        for f in FILES:
            if 'catalog/models' in f:
                try:
                    if 'CheckConstraint' in Path(f).read_text(errors='ignore'): found=['CheckConstraint']; break
                except: pass
    if rg == 'RG-11' and not found:
        try:
            if has_field(apps.get_model('deductions','DeductionTransmission'),'expires_at'): found=['expires_at']
        except: pass
    if found: print(f"  ✓ {rg}"); rg_ok += 1
    else: print(f"  ✗ {rg}")
print(f"  → {rg_ok}/23")

TESTS = ['test_order_creation_decreases_stock','test_order_creation_fails_if_stock_insufficient',
'test_unit_price_frozen_after_product_price_change','test_validate_order_creates_deduction_transmission',
'test_reject_order_restores_stock','test_cannot_validate_already_validated_order',
'test_export_batch_creates_csv_and_updates_status','test_export_returns_none_when_nothing_pending',
'test_users_are_isolated_by_organization','test_same_email_allowed_across_different_organizations',
'test_delivery_created_on_validation','test_delivery_retry_limit_3','test_delivered_closes_order',
'test_low_stock_alert_triggered','test_negative_stock_forbidden']
print("\n=== TESTS ===")
t_ok = sum(1 for t in TESTS if has_func(t))
for t in TESTS: print(f"  {'✓' if has_func(t) else '✗'} {t}")
print(f"  → {t_ok}/{len(TESTS)}")

s_m = (ok_m + 0.5*part_m) / len(PRD)
s_rg = rg_ok / 23
s_t = t_ok / len(TESTS)
score = (s_m*0.35 + s_rg*0.40 + s_t*0.25) * 100
print(f"\n{'='*60}\n  🎯 SCORE: {score:.1f}%\n{'='*60}")
