from django import template

register = template.Library()

CAT_ICONS = {
    "fournitures": ("📄", "#3b82f6"),
    "informatique": ("💻", "#8b5cf6"),
    "epi": ("🦺", "#f59e0b"),
    "mobilier": ("🪑", "#10b981"),
    "aéronautiques": ("✈️", "#06b6d4"),
    "aeronautiques": ("✈️", "#06b6d4"),
    "consommables": ("🧴", "#ec4899"),
    "maintenance": ("🔧", "#64748b"),
    "transport": ("🚚", "#f97316"),
}
DEFAULT_ICON = ("📦", "#6b7280")


@register.simple_tag
def product_icon(product):
    """Retourne (emoji, couleur) selon la catégorie du produit."""
    cat_name = (getattr(getattr(product, "category", None), "name", "") or "").lower()
    for key, val in CAT_ICONS.items():
        if key in cat_name:
            return val
    return DEFAULT_ICON
