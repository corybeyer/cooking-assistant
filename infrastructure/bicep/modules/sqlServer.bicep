// ============================================
// Azure SQL Server and Database
// Stores recipes, ingredients, and steps
// ============================================

@description('Name of the SQL server')
param serverName string

@description('Name of the SQL database')
param databaseName string

@description('Azure region')
param location string

@description('Resource tags')
param tags object = {}

@description('SQL administrator login')
param adminLogin string

@description('SQL administrator password')
@secure()
param adminPassword string

@description('Database SKU name')
param skuName string = 'Basic'

@description('Database DTU capacity')
param skuCapacity int = 5

// ============================================
// Resources
// ============================================

resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: serverName
  location: location
  tags: tags
  properties: {
    administratorLogin: adminLogin
    administratorLoginPassword: adminPassword
    version: '12.0'
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

// Allow Azure services to access the server
resource sqlServerFirewallAzure 'Microsoft.Sql/servers/firewallRules@2023-05-01-preview' = {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-05-01-preview' = {
  parent: sqlServer
  name: databaseName
  location: location
  tags: tags
  sku: {
    name: skuName
    capacity: skuCapacity
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: 2147483648 // 2GB
    catalogCollation: 'SQL_Latin1_General_CP1_CI_AS'
    zoneRedundant: false
    readScale: 'Disabled'
    requestedBackupStorageRedundancy: 'Local'
  }
}

// ============================================
// Outputs
// ============================================

@description('SQL Server fully qualified domain name')
output fullyQualifiedDomainName string = sqlServer.properties.fullyQualifiedDomainName

@description('SQL Server resource ID')
output serverId string = sqlServer.id

@description('SQL Database resource ID')
output databaseId string = sqlDatabase.id
