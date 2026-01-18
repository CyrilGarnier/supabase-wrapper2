#!/bin/bash

# Script de test pour l'API BaseGenspark
# Usage: ./test_api.sh https://votre-api.onrender.com

API_URL="${1:-http://localhost:8000}"

echo "🧪 Tests de l'API BaseGenspark"
echo "================================"
echo "API URL: $API_URL"
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Health check
echo "Test 1: Health Check"
response=$(curl -s -w "\n%{http_code}" "$API_URL/health")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Health check OK"
    echo "  Response: $body"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
fi
echo ""

# Test 2: Get all logs
echo "Test 2: Lire tous les logs"
response=$(curl -s -w "\n%{http_code}" "$API_URL/logs")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Lecture des logs OK"
    count=$(echo "$body" | grep -o '"count":[0-9]*' | grep -o '[0-9]*')
    echo "  Nombre de logs: $count"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
fi
echo ""

# Test 3: Create a log
echo "Test 3: Créer un log"
response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/logs" \
    -H "Content-Type: application/json" \
    -d '{
        "agent_name": "test_script",
        "action": "test_automatise",
        "details": {"timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S)'", "test_id": "test3"}
    }')
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Création de log OK"
    log_id=$(echo "$body" | grep -o '"id":[0-9]*' | grep -o '[0-9]*' | head -1)
    echo "  ID créé: $log_id"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
    log_id=""
fi
echo ""

# Test 4: Get log by ID
if [ -n "$log_id" ]; then
    echo "Test 4: Lire le log créé (ID: $log_id)"
    response=$(curl -s -w "\n%{http_code}" "$API_URL/logs/$log_id")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASS${NC} - Lecture du log par ID OK"
    else
        echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
    fi
    echo ""
fi

# Test 5: Get logs by agent
echo "Test 5: Lire les logs de 'test_script'"
response=$(curl -s -w "\n%{http_code}" "$API_URL/logs/agent/test_script")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Filtrage par agent OK"
    count=$(echo "$body" | grep -o '"count":[0-9]*' | grep -o '[0-9]*')
    echo "  Logs de test_script: $count"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
fi
echo ""

# Test 6: Get recent logs
echo "Test 6: Lire les 5 derniers logs"
response=$(curl -s -w "\n%{http_code}" "$API_URL/logs/recent?limit=5")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Logs récents OK"
    count=$(echo "$body" | grep -o '"count":[0-9]*' | grep -o '[0-9]*')
    echo "  Derniers logs: $count"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
fi
echo ""

# Test 7: Get stats
echo "Test 7: Statistiques globales"
response=$(curl -s -w "\n%{http_code}" "$API_URL/stats")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Statistiques OK"
    total=$(echo "$body" | grep -o '"total_logs":[0-9]*' | grep -o '[0-9]*')
    unique=$(echo "$body" | grep -o '"unique_agents":[0-9]*' | grep -o '[0-9]*')
    echo "  Total logs: $total"
    echo "  Agents uniques: $unique"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
fi
echo ""

# Test 8: Update log
if [ -n "$log_id" ]; then
    echo "Test 8: Mise à jour du log (ID: $log_id)"
    response=$(curl -s -w "\n%{http_code}" -X PUT "$API_URL/logs/$log_id" \
        -H "Content-Type: application/json" \
        -d '{
            "details": {"updated": true, "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S)'"}
        }')
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASS${NC} - Mise à jour OK"
    else
        echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
    fi
    echo ""
fi

# Test 9: Batch create
echo "Test 9: Création en batch (3 logs)"
response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/logs/batch" \
    -H "Content-Type: application/json" \
    -d '[
        {"agent_name": "batch_test", "action": "action1", "details": {"index": 1}},
        {"agent_name": "batch_test", "action": "action2", "details": {"index": 2}},
        {"agent_name": "batch_test", "action": "action3", "details": {"index": 3}}
    ]')
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Création batch OK"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
fi
echo ""

# Test 10: Delete log
if [ -n "$log_id" ]; then
    echo "Test 10: Suppression du log (ID: $log_id)"
    response=$(curl -s -w "\n%{http_code}" -X DELETE "$API_URL/logs/$log_id")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASS${NC} - Suppression OK"
    else
        echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
    fi
    echo ""
fi

echo "================================"
echo "Tests terminés !"
echo ""
echo "Pour voir la documentation interactive:"
echo "  Ouvrez $API_URL/docs dans votre navigateur"
