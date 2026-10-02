#!/bin/bash
# ============================================================
# Extrait les 12 fichiers critiques pour audit GroupPay
# ============================================================

OUT="grouppay_critical_12.txt"

FILES=(
    # --- MODÈLES (8) ---
    "apps/core/models.py"
    "apps/organizations/models.py"
    "apps/accounts/models.py"
    "apps/catalog/models.py"
    "apps/orders/models.py"
    "apps/deductions/models.py"
    "apps/deliveries/models.py"
    "apps/documents/models.py"
    # --- SERVICES + CONFIG + TESTS (4) ---
    "apps/orders/services.py"
    "apps/deliveries/services.py"
    "apps/catalog/services.py"
    "config/settings/base.py"
)

# Compteur
i=0
total=${#FILES[@]}

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  EXTRACTION DES 12 FICHIERS CRITIQUES — GROUPPAY            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# En-tête du fichier de sortie
{
    echo "======================================================================"
    echo "GROUPPAY — EXPORT DES 12 FICHIERS CRITIQUES"
    echo "Généré le : $(date '+%Y-%m-%d %H:%M:%S')"
    echo "======================================================================"
    echo ""
} > "$OUT"

# Boucle sur chaque fichier
for f in "${FILES[@]}"; do
    i=$((i+1))
    if [ -f "$f" ]; then
        size=$(wc -l < "$f" 2>/dev/null || echo "?")
        echo "  [$i/$total] ✓ $f  ($size lignes)"
        {
            echo ""
            echo "======================================================================"
            echo "### FICHIER $i/$total : $f"
            echo "======================================================================"
            echo ""
            cat "$f"
            echo ""
        } >> "$OUT"
    else
        echo "  [$i/$total] ✗ $f  (MANQUANT)"
        {
            echo ""
            echo "======================================================================"
            echo "### FICHIER $i/$total : $f  [FICHIER MANQUANT]"
            echo "======================================================================"
            echo ""
        } >> "$OUT"
    fi
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ Export terminé : $OUT"
echo "  📄 Taille : $(wc -l < "$OUT") lignes / $(du -h "$OUT" | cut -f1)"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "👉 Prochaine étape : affiche le contenu avec :"
echo ""
echo "     cat $OUT"
echo ""
echo "   Puis copie TOUT le contenu et colle-le dans le chat."
echo ""
