// ============================================
// Container Apps Environment
// Shared environment for Container Apps
// ============================================

@description('Name of the Container Apps environment')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object = {}

@description('Log Analytics workspace resource ID')
param logAnalyticsWorkspaceId string

// ============================================
// Resources
// ============================================

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2022-10-01').customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2022-10-01').primarySharedKey
      }
    }
    zoneRedundant: false
  }
}

// ============================================
// Outputs
// ============================================

@description('Container Apps environment ID')
output environmentId string = containerAppsEnvironment.id

@description('Container Apps environment name')
output name string = containerAppsEnvironment.name

@description('Container Apps environment default domain')
output defaultDomain string = containerAppsEnvironment.properties.defaultDomain
