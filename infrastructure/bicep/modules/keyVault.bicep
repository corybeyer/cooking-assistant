// ============================================
// Azure Key Vault
// Securely stores application secrets
// ============================================

@description('Name of the Key Vault')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object = {}

@description('SQL connection string')
@secure()
param sqlConnectionString string

@description('Anthropic API key')
@secure()
param anthropicApiKey string

// ============================================
// Resources
// ============================================

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: false // Set to true for production
    publicNetworkAccess: 'Enabled'
  }
}

// Store SQL password as secret
resource sqlPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'sql-connection-string'
  properties: {
    value: sqlConnectionString
    contentType: 'text/plain'
  }
}

// Store Anthropic API key as secret
resource anthropicSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'anthropic-api-key'
  properties: {
    value: anthropicApiKey
    contentType: 'text/plain'
  }
}

// ============================================
// Outputs
// ============================================

@description('Key Vault name')
output name string = keyVault.name

@description('Key Vault resource ID')
output id string = keyVault.id

@description('Key Vault URI')
output uri string = keyVault.properties.vaultUri

@description('SQL password secret URI')
output sqlPasswordSecretUri string = sqlPasswordSecret.properties.secretUri

@description('Anthropic API key secret URI')
output anthropicApiKeySecretUri string = anthropicSecret.properties.secretUri
