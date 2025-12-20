// ============================================
// Log Analytics Workspace
// Required for Container Apps monitoring
// ============================================

@description('Name of the Log Analytics workspace')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object = {}

@description('Retention period in days')
param retentionInDays int = 30

// ============================================
// Resources
// ============================================

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionInDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ============================================
// Outputs
// ============================================

@description('Log Analytics workspace ID')
output workspaceId string = logAnalyticsWorkspace.id

@description('Log Analytics workspace customer ID')
output customerId string = logAnalyticsWorkspace.properties.customerId

@description('Log Analytics workspace shared key')
output sharedKey string = logAnalyticsWorkspace.listKeys().primarySharedKey
