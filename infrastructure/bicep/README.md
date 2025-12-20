# Infrastructure as Code - Azure Bicep

This directory contains Azure Bicep templates to deploy the complete Cooking Assistant infrastructure.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Azure Resource Group                             │
│                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │ Container Registry│    │    Key Vault     │    │  Log Analytics   │  │
│  │   (Docker images) │    │    (Secrets)     │    │   (Monitoring)   │  │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘  │
│           │                       │                        │            │
│           ▼                       ▼                        ▼            │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   Container Apps Environment                      │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │                     Container App                           │  │  │
│  │  │  ┌─────────────────┐  ┌─────────────────────────────────┐  │  │  │
│  │  │  │ Managed Identity │  │  Cooking Assistant (Streamlit)  │  │  │  │
│  │  │  │  - ACR Pull      │  │  - Port 80                      │  │  │  │
│  │  │  │  - KV Secrets    │  │  - Auto-scaling 0-3 replicas    │  │  │  │
│  │  │  └─────────────────┘  └─────────────────────────────────┘  │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│                                    ▼                                    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                        Azure SQL Server                           │  │
│  │                    ┌────────────────────┐                        │  │
│  │                    │  SQL Database      │                        │  │
│  │                    │  (Recipes, Steps)  │                        │  │
│  │                    └────────────────────┘                        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Resources Created

| Resource | Description | SKU |
|----------|-------------|-----|
| **Container Registry** | Stores Docker images | Basic |
| **SQL Server** | Managed SQL Server | - |
| **SQL Database** | Recipe data storage | Basic (5 DTU) |
| **Key Vault** | Stores secrets (API keys, passwords) | Standard |
| **Log Analytics** | Monitoring and logging | PerGB2018 |
| **Container Apps Environment** | Shared environment | Consumption |
| **Container App** | The application | 0.5 CPU, 1GB RAM |
| **Managed Identity** | Secure access to ACR and Key Vault | - |

## Prerequisites

1. **Azure CLI** (2.50+)
   ```bash
   az --version
   ```

2. **Bicep CLI** (included with Azure CLI 2.50+)
   ```bash
   az bicep version
   ```

3. **Azure subscription** with permissions to create resources

## Deployment

### 1. Login to Azure

```bash
az login
az account set --subscription "<your-subscription-id>"
```

### 2. Create Resource Group

```bash
# Development
az group create --name rg-cooking-assistant-dev --location eastus

# Production
az group create --name rg-cooking-assistant-prod --location eastus
```

### 3. Deploy Infrastructure

```bash
# Development
az deployment group create \
  --resource-group rg-cooking-assistant-dev \
  --template-file infrastructure/bicep/main.bicep \
  --parameters infrastructure/bicep/parameters/dev.bicepparam \
  --parameters sqlAdminPassword='<your-secure-password>' \
  --parameters anthropicApiKey='<your-anthropic-key>'

# Production
az deployment group create \
  --resource-group rg-cooking-assistant-prod \
  --template-file infrastructure/bicep/main.bicep \
  --parameters infrastructure/bicep/parameters/prod.bicepparam \
  --parameters sqlAdminPassword='<your-secure-password>' \
  --parameters anthropicApiKey='<your-anthropic-key>'
```

### 4. Initialize Database

After deployment, run the schema script:

```bash
# Get SQL Server FQDN from deployment output
SQL_SERVER=$(az deployment group show \
  --resource-group rg-cooking-assistant-dev \
  --name main \
  --query properties.outputs.sqlServerFqdn.value -o tsv)

# Connect and run schema
sqlcmd -S $SQL_SERVER -d sqldb-dev-cooking-assistant -U sqladmin -P '<password>' \
  -i infrastructure/schema.sql
```

### 5. Build and Push Container Image

```bash
# Get ACR name from deployment output
ACR_NAME=$(az deployment group show \
  --resource-group rg-cooking-assistant-dev \
  --name main \
  --query properties.outputs.acrLoginServer.value -o tsv)

# Login to ACR
az acr login --name $ACR_NAME

# Build and push
docker build -t $ACR_NAME/cooking-assistant:latest .
docker push $ACR_NAME/cooking-assistant:latest
```

### 6. Update Container App with New Image

```bash
az containerapp update \
  --name ca-dev-cooking-assistant \
  --resource-group rg-cooking-assistant-dev \
  --image $ACR_NAME/cooking-assistant:latest
```

## Module Structure

```
infrastructure/bicep/
├── main.bicep                      # Main orchestration template
├── modules/
│   ├── containerApp.bicep          # Container App + Managed Identity
│   ├── containerAppsEnvironment.bicep  # Container Apps Environment
│   ├── containerRegistry.bicep     # Azure Container Registry
│   ├── keyVault.bicep              # Key Vault + Secrets
│   ├── logAnalytics.bicep          # Log Analytics Workspace
│   └── sqlServer.bicep             # SQL Server + Database
├── parameters/
│   ├── dev.bicepparam              # Development parameters
│   └── prod.bicepparam             # Production parameters
└── README.md                       # This file
```

## Security Features

- **Managed Identity**: No credentials stored in code; Container App uses managed identity to:
  - Pull images from Container Registry
  - Read secrets from Key Vault
- **Key Vault**: All secrets stored securely (DB password, API keys)
- **RBAC**: Role-based access control for all resources
- **TLS 1.2**: Minimum TLS version for SQL Server
- **Private networking**: Can be enhanced with VNet integration (not included)

## Scaling

The Container App is configured with:
- **Min replicas**: 0 (scales to zero when idle)
- **Max replicas**: 3
- **Scale rule**: HTTP concurrent requests (50 per instance)

Modify in `modules/containerApp.bicep` or override with parameters.

## Cost Optimization

Development defaults use minimal SKUs:
- SQL Database: Basic (5 DTU) ~$5/month
- Container Registry: Basic ~$5/month
- Container Apps: Consumption (pay per use)
- Key Vault: Standard (pay per operation)

**Estimated dev cost**: ~$15-30/month (depending on usage)

## Cleanup

```bash
# Delete all resources
az group delete --name rg-cooking-assistant-dev --yes --no-wait
```

## Troubleshooting

### View Container App Logs
```bash
az containerapp logs show \
  --name ca-dev-cooking-assistant \
  --resource-group rg-cooking-assistant-dev \
  --follow
```

### Check Deployment Status
```bash
az containerapp revision list \
  --name ca-dev-cooking-assistant \
  --resource-group rg-cooking-assistant-dev \
  --output table
```

### Validate Bicep Templates
```bash
az bicep build --file infrastructure/bicep/main.bicep
```
