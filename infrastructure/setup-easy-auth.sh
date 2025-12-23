#!/bin/bash
# ============================================
# Setup Azure Container Apps Easy Auth with Entra ID
# ============================================
# This script configures authentication for your Container App
# so users must sign in with Microsoft Entra ID (Azure AD).
#
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - An existing Container App deployed
#   - Permissions to create App Registrations in Entra ID
#
# Usage:
#   ./setup-easy-auth.sh <resource-group> <container-app-name>
#
# Example:
#   ./setup-easy-auth.sh rg-cooking-assistant-dev ca-dev-cooking-assistant
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -lt 2 ]; then
    echo -e "${RED}Usage: $0 <resource-group> <container-app-name>${NC}"
    echo "Example: $0 rg-cooking-assistant-dev ca-dev-cooking-assistant"
    exit 1
fi

RESOURCE_GROUP=$1
CONTAINER_APP=$2

echo -e "${GREEN}Setting up Easy Auth for ${CONTAINER_APP}...${NC}"

# Step 1: Get the Container App's FQDN
echo -e "${YELLOW}Step 1: Getting Container App URL...${NC}"
APP_URL=$(az containerapp show \
    --name "$CONTAINER_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" \
    --output tsv)

if [ -z "$APP_URL" ]; then
    echo -e "${RED}Error: Could not get Container App URL. Is the app deployed?${NC}"
    exit 1
fi

REDIRECT_URI="https://${APP_URL}/.auth/login/aad/callback"
echo "  App URL: https://${APP_URL}"
echo "  Redirect URI: ${REDIRECT_URI}"

# Step 2: Create Entra ID App Registration
echo -e "${YELLOW}Step 2: Creating Entra ID App Registration...${NC}"
APP_NAME="${CONTAINER_APP}-auth"

# Check if app already exists
EXISTING_APP=$(az ad app list --display-name "$APP_NAME" --query "[0].appId" -o tsv 2>/dev/null || true)

if [ -n "$EXISTING_APP" ]; then
    echo "  App Registration already exists: $EXISTING_APP"
    CLIENT_ID=$EXISTING_APP
else
    # Create new app registration
    CLIENT_ID=$(az ad app create \
        --display-name "$APP_NAME" \
        --sign-in-audience "AzureADMyOrg" \
        --web-redirect-uris "$REDIRECT_URI" \
        --query "appId" \
        --output tsv)
    echo "  Created App Registration: $CLIENT_ID"
fi

# Step 3: Create client secret
echo -e "${YELLOW}Step 3: Creating client secret...${NC}"
CLIENT_SECRET=$(az ad app credential reset \
    --id "$CLIENT_ID" \
    --display-name "EasyAuthSecret" \
    --query "password" \
    --output tsv)
echo "  Client secret created (save this - it won't be shown again!)"

# Step 4: Get tenant ID
TENANT_ID=$(az account show --query "tenantId" --output tsv)
echo "  Tenant ID: $TENANT_ID"

# Step 5: Enable Easy Auth on Container App
echo -e "${YELLOW}Step 4: Enabling Easy Auth on Container App...${NC}"
az containerapp auth microsoft update \
    --name "$CONTAINER_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --client-id "$CLIENT_ID" \
    --client-secret "$CLIENT_SECRET" \
    --tenant-id "$TENANT_ID" \
    --yes

# Enable authentication requirement
az containerapp auth update \
    --name "$CONTAINER_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --unauthenticated-client-action RedirectToLoginPage \
    --enabled true

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Easy Auth Setup Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Configuration Summary:"
echo "  Container App: $CONTAINER_APP"
echo "  App URL: https://${APP_URL}"
echo "  Client ID: $CLIENT_ID"
echo "  Tenant ID: $TENANT_ID"
echo ""
echo -e "${YELLOW}Important: Save these values!${NC}"
echo "  CLIENT_SECRET: $CLIENT_SECRET"
echo ""
echo "Users in your Entra ID tenant can now sign in at:"
echo "  https://${APP_URL}"
echo ""
echo "To test locally, set these environment variables:"
echo "  export DEV_USER_ID='your-entra-object-id'"
echo "  export DEV_USER_NAME='Your Name'"
echo ""
echo "To find your Entra Object ID, run:"
echo "  az ad signed-in-user show --query id -o tsv"
