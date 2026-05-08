#!/bin/bash
# Check demo auto status and MT5 bridge
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"admin","password":"admin12345678"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

echo "=== Demo Auto Status ==="
curl -s http://localhost:8000/api/v1/trades/demo-auto/status \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "=== MT5 Bridge Health ==="
curl -s http://localhost:8000/api/v1/mt5/health \
  -H "Authorization: Bearer $TOKEN" 2>&1 | head -20

echo ""
echo "=== System Runtime ==="
curl -s http://localhost:8000/api/v1/system/runtime \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "=== MT5 Bridge Service ==="
systemctl is-active mt5-bridge 2>/dev/null || echo "mt5-bridge service not found"
systemctl is-active openclaw-runtime 2>/dev/null || echo "openclaw-runtime service not found"

echo ""
echo "=== Demo Auto Start ==="
curl -s -X POST http://localhost:8000/api/v1/trades/demo-auto/start \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' | python3 -m json.tool