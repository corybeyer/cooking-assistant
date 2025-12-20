// ============================================
// Cooking Assistant - Main Infrastructure
// Azure Bicep Template
// ============================================

targetScope = 'resourceGroup'

// ============================================
// Parameters
// ============================================

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Base name for all resources')
param baseName string = 'cooking-assistant'

@description('SQL Server administrator login')
param sqlAdminLogin string = 'sqladmin'

@description('SQL Server administrator password')
@secure()
param sqlAdminPassword string

@description('Anthropic API key for Claude')
@secure()
param anthropicApiKey string

@description('Container image tag to deploy')
param imageTag string = 'latest'

// ============================================
// Variables
// ============================================

var resourcePrefix = '${environment}-${baseName}'
var tags = {
  Environment: environment
  Application: 'Cooking Assistant'
  ManagedBy: 'Bicep'
}

// Sanitized names (Azure naming restrictions)
var acrName = replace('acr${baseName}${environment}', '-', '')
var sqlServerName = 'sql-${resourcePrefix}'
var sqlDatabaseName = 'sqldb-${resourcePrefix}'
var keyVaultName = 'kv-${take(replace(resourcePrefix, '-', ''), 20)}'
var logAnalyticsName = 'log-${resourcePrefix}'
var containerAppEnvName = 'cae-${resourcePrefix}'
var containerAppName = 'ca-${resourcePrefix}'

// ============================================
// Modules
// ============================================

// Log Analytics Workspace (required for Container Apps)
module logAnalytics 'modules/logAnalytics.bicep' = {
  name: 'logAnalytics'
  params: {
    name: logAnalyticsName
    location: location
    tags: tags
  }
}

// Azure Container Registry
module containerRegistry 'modules/containerRegistry.bicep' = {
  name: 'containerRegistry'
  params: {
    name: acrName
    location: location
    tags: tags
  }
}

// Key Vault for secrets
module keyVault 'modules/keyVault.bicep' = {
  name: 'keyVault'
  params: {
    name: keyVaultName
    location: location
    tags: tags
    sqlConnectionString: 'Server=tcp:${sqlServer.outputs.fullyQualifiedDomainName},1433;Database=${sqlDatabaseName};User ID=${sqlAdminLogin};Password=${sqlAdminPassword};Encrypt=True;TrustServerCertificate=False;'
    anthropicApiKey: anthropicApiKey
  }
}

// Azure SQL Server and Database
module sqlServer 'modules/sqlServer.bicep' = {
  name: 'sqlServer'
  params: {
    serverName: sqlServerName
    databaseName: sqlDatabaseName
    location: location
    tags: tags
    adminLogin: sqlAdminLogin
    adminPassword: sqlAdminPassword
  }
}

// Container Apps Environment
module containerAppsEnv 'modules/containerAppsEnvironment.bicep' = {
  name: 'containerAppsEnv'
  params: {
    name: containerAppEnvName
    location: location
    tags: tags
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
  }
}

// Container App
module containerApp 'modules/containerApp.bicep' = {
  name: 'containerApp'
  params: {
    name: containerAppName
    location: location
    tags: tags
    containerAppsEnvironmentId: containerAppsEnv.outputs.environmentId
    containerRegistryName: containerRegistry.outputs.name
    containerRegistryLoginServer: containerRegistry.outputs.loginServer
    imageName: 'cooking-assistant'
    imageTag: imageTag
    keyVaultName: keyVault.outputs.name
    dbServer: sqlServer.outputs.fullyQualifiedDomainName
    dbName: sqlDatabaseName
    dbUser: sqlAdminLogin
    dbPasswordSecretUri: keyVault.outputs.sqlPasswordSecretUri
    anthropicApiKeySecretUri: keyVault.outputs.anthropicApiKeySecretUri
  }
}

// ============================================
// Outputs
// ============================================

@description('Container App URL')
output containerAppUrl string = containerApp.outputs.url

@description('Container Registry login server')
output acrLoginServer string = containerRegistry.outputs.loginServer

@description('SQL Server FQDN')
output sqlServerFqdn string = sqlServer.outputs.fullyQualifiedDomainName

@description('Key Vault name')
output keyVaultName string = keyVault.outputs.name

@description('Resource Group name')
output resourceGroupName string = resourceGroup().name
