// ============================================
// Azure Container Registry
// Stores Docker images for the application
// ============================================

@description('Name of the container registry (must be globally unique)')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object = {}

@description('SKU for the container registry')
@allowed(['Basic', 'Standard', 'Premium'])
param sku string = 'Basic'

// ============================================
// Resources
// ============================================

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
    policies: {
      retentionPolicy: {
        status: 'enabled'
        days: 30
      }
    }
  }
}

// ============================================
// Outputs
// ============================================

@description('Container registry name')
output name string = containerRegistry.name

@description('Container registry login server')
output loginServer string = containerRegistry.properties.loginServer

@description('Container registry resource ID')
output id string = containerRegistry.id
