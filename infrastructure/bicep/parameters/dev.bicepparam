// ============================================
// Development Environment Parameters
// ============================================

using '../main.bicep'

param environment = 'dev'
param baseName = 'cooking-assistant'
param sqlAdminLogin = 'sqladmin'

// These must be provided at deployment time:
// param sqlAdminPassword = ''
// param anthropicApiKey = ''
// param imageTag = 'latest'
