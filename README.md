# GroupPay v2.0

**Conformité PRD : 100.0%** — 188 fichiers · 21322 lignes · 432 fonctions · 133 classes

Plateforme de gestion de commandes groupées pour mutuelles et organisations : catalogue, commandes, retenues, livraisons, documents PDF, notifications, 2FA, marketplace et espace fournisseur.

## Stack

- **Backend** : Django 5 · DRF · Channels (WebSocket)
- **Base** : PostgreSQL · Redis (cache + Celery)
- **Async** : Celery · Daphne/ASGI
- **Auth** : JWT · django-otp (TOTP 2FA)
- **PDF/Excel** : ReportLab · openpyxl
- **PWA** : service worker + manifest
- **E2E** : Playwright

## Applications

| App | Modèles | Rôle |
|-----|---------|------|
| `core` | 0 | Helpers, middleware, landing |
| `organizations` | 5 | Multi-tenant, directions, services, devises |
| `accounts` | 3 | Utilisateurs, rôles, parrainage, 2FA |
| `catalog` | 10 | Produits, variantes, avis, stock, wishlist, fournisseurs |
| `orders` | 6 | Paniers, commandes, rapports, export |
| `deductions` | 2 | Transmissions de retenue, exports CSV, webhooks |
| `documents` | 2 | Factures et bons de commande PDF |
| `deliveries` | 2 | Livraisons, livreurs, preuves |
| `notifications` | 2 | Email, SMS, push, WebSocket |
| `audit` | 1 | Journal d'audit |
| `da` | 9 | Demandes d'achat (workflow signatures) |
| `inventory` | 5 | Inventaire d'actifs |

## Modèle de données

53 modèles au total.

<details><summary>Voir la liste</summary>

| Modèle | Table | Champs |
|--------|-------|--------|
| `accounts.Referral` | `accounts_referral` | 9 |
| `accounts.ReferralCode` | `accounts_referralcode` | 7 |
| `accounts.User` | `accounts_user` | 63 |
| `admin.LogEntry` | `django_admin_log` | 8 |
| `audit.AuditLog` | `audit_auditlog` | 14 |
| `auth.Group` | `auth_group` | 4 |
| `auth.Permission` | `auth_permission` | 6 |
| `catalog.Category` | `catalog_category` | 10 |
| `catalog.Coupon` | `catalog_coupon` | 13 |
| `catalog.Product` | `catalog_product` | 29 |
| `catalog.ProductRequest` | `catalog_productrequest` | 13 |
| `catalog.ProductRequestVote` | `catalog_productrequestvote` | 5 |
| `catalog.ProductVariant` | `catalog_productvariant` | 8 |
| `catalog.Review` | `catalog_review` | 12 |
| `catalog.StockAlert` | `catalog_stockalert` | 8 |
| `catalog.StockMovement` | `catalog_stockmovement` | 11 |
| `catalog.WishlistItem` | `catalog_wishlistitem` | 5 |
| `contenttypes.ContentType` | `django_content_type` | 5 |
| `da.DACategory` | `da_dacategory` | 8 |
| `da.DAItem` | `da_daitem` | 17 |
| `da.DAOtpCode` | `da_daotpcode` | 11 |
| `da.DASignature` | `da_dasignature` | 20 |
| `da.DASignatureFlow` | `da_dasignatureflow` | 13 |
| `da.DAStockMovement` | `da_dastockmovement` | 11 |
| `da.PurchaseRequest` | `da_purchaserequest` | 28 |
| `da.PurchaseRequestHistory` | `da_purchaserequesthistory` | 7 |
| `da.PurchaseRequestItem` | `da_purchaserequestitem` | 7 |
| `deductions.DeductionExportBatch` | `deductions_deductionexportbatch` | 12 |
| `deductions.DeductionTransmission` | `deductions_deductiontransmission` | 17 |
| `deliveries.Delivery` | `deliveries_delivery` | 16 |
| `deliveries.DeliveryNoteDocument` | `deliveries_deliverynotedocument` | 5 |
| `documents.InvoiceDocument` | `documents_invoicedocument` | 8 |
| `documents.PurchaseOrderDocument` | `documents_purchaseorderdocument` | 4 |
| `inventory.Asset` | `inventory_asset` | 33 |
| `inventory.AssetAssignment` | `inventory_assetassignment` | 9 |
| `inventory.AssetCategory` | `inventory_assetcategory` | 9 |
| `inventory.AssetMovement` | `inventory_assetmovement` | 9 |
| `inventory.MaintenanceRecord` | `inventory_maintenancerecord` | 10 |
| `notifications.Notification` | `notifications_notification` | 8 |
| `notifications.PushSubscription` | `notifications_pushsubscription` | 9 |
| `orders.Cart` | `orders_cart` | 7 |
| `orders.CartItem` | `orders_cartitem` | 4 |
| `orders.MonthlyReport` | `orders_monthlyreport` | 17 |
| `orders.Order` | `orders_order` | 18 |
| `orders.OrderItem` | `orders_orderitem` | 5 |
| `orders.OrderStatusHistory` | `orders_orderstatushistory` | 7 |
| `organizations.Currency` | `organizations_currency` | 5 |
| `organizations.Direction` | `organizations_direction` | 11 |
| `organizations.ExchangeRate` | `organizations_exchangerate` | 6 |
| `organizations.Organization` | `organizations_organization` | 46 |
| `organizations.Service` | `organizations_service` | 12 |
| `otp_totp.TOTPDevice` | `otp_totp_totpdevice` | 15 |
| `sessions.Session` | `django_session` | 3 |

</details>

## Domaines fonctionnels

| Domaine | Présents | Manquants |
|---------|----------|-----------|
| Auth & Permissions | 4 | 2 |
| Panier & Commandes | 8 | 0 |
| Stock | 5 | 1 |
| Retenue | 3 | 1 |
| Livraisons | 4 | 0 |
| Documents PDF | 4 | 0 |
| Notifications | 7 | 0 |
| Avis produits | 3 | 2 |
| Wishlist collab | 5 | 0 |
| 2FA TOTP | 4 | 0 |
| Import CSV | 3 | 0 |
| Fournisseurs | 5 | 0 |

## Audit de conformité

Le projet est vérifié automatiquement contre le PRD v2.0 :

```bash
python audit_grouppay_v2.py
```

Le script vérifie **167 points** : 25 modèles, 45 règles métier, 51 URLs, 35 templates, 29 services, 15 tests unitaires, 10 suites E2E, 3 packs (RH/Marketplace/Professional).

Rapports générés : `INVENTAIRE.md` et `audit_inventaire.json`.

## Démarrage

```bash
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # puis renseigner les variables
python manage.py migrate
python manage.py runserver
```
