#!/bin/bash
# Script de lancement des tests E2E
# Prerequis : serveur Django deja lance sur http://127.0.0.1:8000

echo "============================================================"
echo "  ZIONPAY E2E TESTS"
echo "============================================================"
echo ""

# Verifier que le serveur est up
if ! curl -s http://127.0.0.1:8000/health/ > /dev/null; then
    echo "XX Le serveur Django n'est pas lance sur http://127.0.0.1:8000"
    echo "   Lance dans un autre terminal : python manage.py runserver"
    exit 1
fi

echo "OK Serveur Django accessible"
echo ""

# Mode
MODE="${1:-all}"

case "$MODE" in
    all)
        echo ">>> Tous les tests E2E"
        pytest tests/e2e/ -m e2e --tb=short
        ;;
    headed)
        echo ">>> Tests E2E avec navigateur visible"
        pytest tests/e2e/ -m e2e --headed --tb=short
        ;;
    slowmo)
        echo ">>> Tests E2E slow-motion"
        pytest tests/e2e/ -m e2e --headed --slowmo 500 --tb=short
        ;;
    smoke)
        echo ">>> Tests smoke (rapides)"
        pytest tests/e2e/test_auth.py tests/e2e/test_navigation.py -m e2e --tb=short
        ;;
    *)
        echo "Usage: ./run_e2e.sh [all|headed|slowmo|smoke]"
        ;;
esac

echo ""
echo "============================================================"
echo "  FIN DES TESTS"
echo "============================================================"
