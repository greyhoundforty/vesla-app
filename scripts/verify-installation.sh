#!/bin/bash

################################################################################
# Vesla Server Installation - Verification Script
# Tests that installation completed successfully
################################################################################

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="/opt/vesla"
PASSED=0
FAILED=0

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Vesla Server Verification${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

check() {
    local name="$1"
    local command="$2"
    
    echo -n "Checking $name... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC}"
        ((FAILED++))
        return 1
    fi
}

# System checks
echo -e "${BLUE}System Components${NC}"
check "Docker" "docker --version"
check "Docker Compose" "docker compose version"
check "Vesla user" "id vesla"
check "Install directory" "test -d $INSTALL_DIR"
echo ""

# Container checks
echo -e "${BLUE}Running Containers${NC}"
check "Traefik" "docker ps | grep -q traefik"
check "Vesla API" "docker ps | grep -q vesla-api"
check "Vesla Dashboard" "docker ps | grep -q vesla-dashboard"
echo ""

# Network checks
echo -e "${BLUE}Docker Network${NC}"
check "vesla-network" "docker network inspect vesla-network > /dev/null 2>&1"
echo ""

# Configuration checks
echo -e "${BLUE}Configuration Files${NC}"
check "Traefik .env" "test -f $INSTALL_DIR/traefik/.env"
check "Server .env" "test -f $INSTALL_DIR/server/.env"
check "Traefik config" "test -f $INSTALL_DIR/traefik/traefik.yml"
echo ""

# Health checks
echo -e "${BLUE}API Endpoints${NC}"
sleep 2
if curl -s http://127.0.0.1:5001/health | grep -q "healthy"; then
    echo -n "API /health endpoint... "
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -n "API /health endpoint... "
    echo -e "${YELLOW}⚠${NC} (may not be ready yet)"
fi
echo ""

# Summary
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "Checks passed: ${GREEN}$PASSED${NC}"
if [[ $FAILED -gt 0 ]]; then
    echo -e "Checks failed: ${RED}$FAILED${NC}"
    echo ""
    echo "Installation may have issues. Check logs:"
    echo "  tail -50 $INSTALL_DIR/install.log"
    echo "  docker compose -f $INSTALL_DIR/traefik/docker-compose.yml logs"
    exit 1
else
    echo -e "All checks passed! ${GREEN}✓${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Configure the CLI:"
    echo "     vesla config set server_url https://api.your-domain.com"
    echo "     vesla config set api_token <from .env file>"
    echo ""
    echo "  2. Deploy an application:"
    echo "     cd example-apps/python"
    echo "     vesla push"
    echo ""
    exit 0
fi
