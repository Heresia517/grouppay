# Inventaire ZionPay v2.0 — 2026-10-10T18:27:27

**Score global PRD : 100.0%**  
**167 OK / 0 échecs / 2 warnings**

## Statistiques

- Fichiers Python : **188**
- Lignes de code : **21322**
- Fonctions : **432**
- Classes : **133**

## Applications Django

| App | Modèles |
|-----|---------|
| daphne | 0 |
| admin | 1 |
| auth | 2 |
| contenttypes | 1 |
| sessions | 1 |
| messages | 0 |
| staticfiles | 0 |
| rest_framework | 0 |
| drf_spectacular | 0 |
| rest_framework_simplejwt | 0 |
| core | 0 |
| organizations | 5 |
| accounts | 3 |
| catalog | 10 |
| orders | 6 |
| deductions | 2 |
| documents | 2 |
| deliveries | 2 |
| notifications | 2 |
| channels | 0 |
| audit | 1 |
| da | 9 |
| inventory | 5 |
| django_otp | 0 |
| otp_totp | 1 |

## Modèles (introspection)

| Modèle | Table | Champs |
|--------|-------|--------|
| accounts.Referral | `accounts_referral` | 9 |
| accounts.ReferralCode | `accounts_referralcode` | 7 |
| accounts.User | `accounts_user` | 63 |
| admin.LogEntry | `django_admin_log` | 8 |
| audit.AuditLog | `audit_auditlog` | 14 |
| auth.Group | `auth_group` | 4 |
| auth.Permission | `auth_permission` | 6 |
| catalog.Category | `catalog_category` | 10 |
| catalog.Coupon | `catalog_coupon` | 13 |
| catalog.Product | `catalog_product` | 29 |
| catalog.ProductRequest | `catalog_productrequest` | 13 |
| catalog.ProductRequestVote | `catalog_productrequestvote` | 5 |
| catalog.ProductVariant | `catalog_productvariant` | 8 |
| catalog.Review | `catalog_review` | 12 |
| catalog.StockAlert | `catalog_stockalert` | 8 |
| catalog.StockMovement | `catalog_stockmovement` | 11 |
| catalog.WishlistItem | `catalog_wishlistitem` | 5 |
| contenttypes.ContentType | `django_content_type` | 5 |
| da.DACategory | `da_dacategory` | 8 |
| da.DAItem | `da_daitem` | 17 |
| da.DAOtpCode | `da_daotpcode` | 11 |
| da.DASignature | `da_dasignature` | 20 |
| da.DASignatureFlow | `da_dasignatureflow` | 13 |
| da.DAStockMovement | `da_dastockmovement` | 11 |
| da.PurchaseRequest | `da_purchaserequest` | 28 |
| da.PurchaseRequestHistory | `da_purchaserequesthistory` | 7 |
| da.PurchaseRequestItem | `da_purchaserequestitem` | 7 |
| deductions.DeductionExportBatch | `deductions_deductionexportbatch` | 12 |
| deductions.DeductionTransmission | `deductions_deductiontransmission` | 17 |
| deliveries.Delivery | `deliveries_delivery` | 16 |
| deliveries.DeliveryNoteDocument | `deliveries_deliverynotedocument` | 5 |
| documents.InvoiceDocument | `documents_invoicedocument` | 8 |
| documents.PurchaseOrderDocument | `documents_purchaseorderdocument` | 4 |
| inventory.Asset | `inventory_asset` | 33 |
| inventory.AssetAssignment | `inventory_assetassignment` | 9 |
| inventory.AssetCategory | `inventory_assetcategory` | 9 |
| inventory.AssetMovement | `inventory_assetmovement` | 9 |
| inventory.MaintenanceRecord | `inventory_maintenancerecord` | 10 |
| notifications.Notification | `notifications_notification` | 8 |
| notifications.PushSubscription | `notifications_pushsubscription` | 9 |
| orders.Cart | `orders_cart` | 7 |
| orders.CartItem | `orders_cartitem` | 4 |
| orders.MonthlyReport | `orders_monthlyreport` | 17 |
| orders.Order | `orders_order` | 18 |
| orders.OrderItem | `orders_orderitem` | 5 |
| orders.OrderStatusHistory | `orders_orderstatushistory` | 7 |
| organizations.Currency | `organizations_currency` | 5 |
| organizations.Direction | `organizations_direction` | 11 |
| organizations.ExchangeRate | `organizations_exchangerate` | 6 |
| organizations.Organization | `organizations_organization` | 46 |
| organizations.Service | `organizations_service` | 12 |
| otp_totp.TOTPDevice | `otp_totp_totpdevice` | 15 |
| sessions.Session | `django_session` | 3 |

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

## Warnings

- SENTRY_DSN absent (opt-in)
- SENTRY_ENVIRONMENT absent (opt-in)

## Fonctions détectées (extrait)

```
__call__, __init__, __str__, _add_history, _auto_width, _can_validate_da, _can_view, _check_permission, _create_signature_flow, _get_achats_director, _get_client_ip, _get_default_context, _get_dg, _get_director_for_service, _get_ip, _get_open_cart, _get_or_create_pdf, _get_vapid_claims, _is_achats, _is_owner, _normalize_vapid_key, _notify, _notify_in_app, _pct_delta, _render_cart_badge, _render_cart_page, _require_admin_da, _require_manager, _require_rh, _require_supplier, _send_email, _send_sms, _serve_sw, _style_header, _style_title, abandoned_carts_list, add_arguments, add_item_to_request, add_to_cart, adjust_stock, admin_categories, admin_category_delete, admin_category_form, admin_credentials, admin_direction_delete, admin_direction_form, admin_directions, admin_home, admin_item_delete, admin_item_form, admin_item_stock_adjust, admin_item_toggle, admin_items, admin_items_import, admin_items_import_template, admin_items_import_upload, admin_service_delete, admin_service_form, admin_services, age_months, api_convert, apply_coupon, apply_referral_code, asset_assign, asset_change_status, asset_detail, asset_form, asset_list, asset_return, assign_asset, assign_courier, attempt_delivery, audit_order, average_rating, base_url, browser_context_args, build_cart_recovery_email_context, bulk_reject_orders, bulk_validate_orders, can_be_used, can_validate, cart_context, cart_recovery_send, cart_recovery_send_all, catalog, category, check_low_stock, check_low_stock_alerts, check_max_per_member, cleanup_expired_carts, cleanup_expired_transmissions, cleanup_invalid_subscriptions, close_request, collect_monthly_data, compute_discount, compute_document_hash, compute_signature_hash, compute_total, computed_value, confirm_deduction, connect, convert_amount, courier, courier_deliveries, create_delivery_for_order, create_from_cart, create_order_from_cart, create_order_view, create_purchase_request, create_signature, create_superuser, create_user, currency_converter, da_cancel_confirm, da_cancel_page, da_close, da_close_page, da_create, da_dashboard, da_dashboard_old, da_detail, da_download_pdf, da_export_excel_list, da_export_single_excel, da_items_catalog, da_list, da_order, da_preview_pdf, da_receive, da_receive_page, da_reject_confirm, da_reject_page, da_sign_page, da_sign_refuse, da_sign_verify, da_stats, da_submit, da_verify_stock, da_visa, decrement_stock, deduction_webhook, deductions_dashboard, delete, delete_product, delete_request, delete_review, delivery, delivery_detail, disconnect, download_batch, download_invoice_pdf, download_purchase_order_pdf, export_da_list_excel, export_dashboard_excel, export_dashboard_pdf, export_setup, export_single_da_excel, for_organization, format_currency, generate_asset_reference, generate_da_number, generate_da_pdf, generate_export, generate_export_batch, generate_invoice_number, generate_invoice_pdf, generate_monthly_report_excel, generate_monthly_report_pdf, generate_monthly_reports, generate_order_number, generate_otp_code, generate_purchase_order_pdf, generate_referral_code, generate_report, generate_verification_qr, generate_visual_signature, get_abandoned_carts, get_cart_recovery_stats, get_category_stats, get_da_document_hash, get_exchange_rate, get_inventory_stats, get_month_range, get_or_create_invoice, get_or_create_referral_code, get_queryset, get_referral_stats, get_session, get_user_totp_device, zionpay_context, h1, h2, handle, has_add_permission, has_change_permission, has_delete_permission, has_module, has_object_permission, has_permission, has_voted
```
