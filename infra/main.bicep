// ──────────────────────────────────────────────
// Root Template: main.bicep
// Orchestrates all Rewind infrastructure modules.
//
// Deployment order (to resolve circular dependency
// between Key Vault and App Service):
//   1. monitoring  — Log Analytics + App Insights
//   2. storage     — Blob Storage
//   3. postgresql  — Database server
//   4. appservice  — App Service Plan + Web Apps
//                    (creates managed identities)
//   5. keyvault    — Key Vault with access policies
//                    for the managed identities
//
// Note: App Service references Key Vault secrets
// via @Microsoft.KeyVault() syntax. On first deploy,
// those references will fail to resolve until KV
// secrets are populated. This is expected — the apps
// will start serving once secrets are set.
// ──────────────────────────────────────────────

targetScope = 'resourceGroup'

// ── Parameters ───────────────────────────────

@description('Deployment environment. Controls SKU selection.')
@allowed([
  'dev'
  'prod'
])
param environment string

@description('Azure region for all resources. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Project name used as a prefix for resource names.')
param projectName string = 'rewind'

@description('PostgreSQL administrator login name.')
param postgresAdminLogin string = 'rewindadmin'

@secure()
@description('PostgreSQL administrator login password.')
param postgresAdminPassword string

// ── SKU Selection ────────────────────────────
// Using lowest-cost SKUs for both environments.
// Burstable B1ms (~$13/mo), App Service B1 (~$13/mo each)
// Upgrade to higher SKUs when needed.

var postgresSkuName = 'Standard_B1ms'
var postgresSkuTier = 'Burstable'
var postgresStorageGB = 32
var appServiceSku = 'B1'

// ── Resource Names ───────────────────────────
// Convention: {project}-{resource}-{env}

var suffix = '${projectName}-${environment}'
var monitoringWorkspaceName = 'log-${suffix}'
var appInsightsName = 'ai-${suffix}'
var postgresServerName = 'pg-${suffix}'
var storageAccountName = 'st${take(uniqueString(resourceGroup().id, projectName), 20)}'  // 3-24 alphanumeric, globally unique
var appServicePlanName = 'plan-${suffix}'
var backendAppName = 'app-backend-${suffix}'
var frontendAppName = 'app-frontend-${suffix}'
var keyVaultName = 'kv-${suffix}'

// Docker images — override these at deploy time
// with actual ACR image references.
var dockerRegistryUrl = 'https://ghcr.io'
var backendImage = '${projectName}/backend:latest'
var frontendImage = '${projectName}/frontend:latest'

// ── 1. Monitoring ────────────────────────────

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring-deployment'
  params: {
    workspaceName: monitoringWorkspaceName
    appInsightsName: appInsightsName
    location: location
  }
}

// ── 2. Storage ───────────────────────────────

module storage 'modules/storage.bicep' = {
  name: 'storage-deployment'
  params: {
    storageAccountName: storageAccountName
    location: location
  }
}

// ── 3. PostgreSQL ────────────────────────────

module postgresql 'modules/postgresql.bicep' = {
  name: 'postgresql-deployment'
  params: {
    serverName: postgresServerName
    location: location
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    skuName: postgresSkuName
    skuTier: postgresSkuTier
    storageSizeGB: postgresStorageGB
  }
}

// ── 4. App Service ───────────────────────────
// Deployed before Key Vault so managed identity
// principal IDs are available for KV access policies.

module appservice 'modules/appservice.bicep' = {
  name: 'appservice-deployment'
  params: {
    planName: appServicePlanName
    backendAppName: backendAppName
    frontendAppName: frontendAppName
    location: location
    sku: appServiceSku
    dockerRegistryUrl: dockerRegistryUrl
    backendImage: backendImage
    frontendImage: frontendImage
    keyVaultName: keyVaultName
    appInsightsConnectionString: monitoring.outputs.connectionString
  }
}

// ── 5. Key Vault ─────────────────────────────
// Deployed after App Service so we can grant the
// managed identities access to secrets.

module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault-deployment'
  params: {
    vaultName: keyVaultName
    location: location
    backendPrincipalId: appservice.outputs.backendPrincipalId
    frontendPrincipalId: appservice.outputs.frontendPrincipalId
  }
}

// ── Outputs ──────────────────────────────────

@description('Backend Web App hostname.')
output backendHostname string = appservice.outputs.backendHostname

@description('Frontend Web App hostname.')
output frontendHostname string = appservice.outputs.frontendHostname

@description('PostgreSQL server FQDN.')
output postgresServerFqdn string = postgresql.outputs.serverFqdn

@description('Storage account name.')
output storageAccountName string = storage.outputs.accountName

@description('Key Vault URI.')
output keyVaultUri string = keyvault.outputs.vaultUri

@description('Application Insights instrumentation key.')
output appInsightsInstrumentationKey string = monitoring.outputs.instrumentationKey
