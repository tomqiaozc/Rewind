// ──────────────────────────────────────────────
// Module: appservice.bicep
// Provisions an App Service Plan (Linux) with
// two Web Apps: backend (Python) and frontend
// (Node.js) for the Rewind platform.
// ──────────────────────────────────────────────

@description('Name of the App Service Plan.')
param planName string

@description('Name of the backend Web App.')
param backendAppName string

@description('Name of the frontend Web App.')
param frontendAppName string

@description('Azure region for all resources.')
param location string

@description('App Service Plan SKU (e.g. B1, P1v3).')
param sku string = 'B1'

@description('Docker registry URL (e.g. https://ghcr.io).')
param dockerRegistryUrl string

@description('Backend Docker image (e.g. myacr.azurecr.io/rewind-backend:latest).')
param backendImage string

@description('Frontend Docker image (e.g. myacr.azurecr.io/rewind-frontend:latest).')
param frontendImage string

@description('Name of the Key Vault used for secret references.')
param keyVaultName string

@description('Application Insights connection string for telemetry.')
param appInsightsConnectionString string

// ── App Service Plan (Linux) ─────────────────

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  kind: 'linux'
  sku: {
    name: sku
  }
  properties: {
    reserved: true // required for Linux
  }
}

// ── Backend Web App ──────────────────────────

resource backendApp 'Microsoft.Web/sites@2023-12-01' = {
  name: backendAppName
  location: location
  kind: 'app,linux,container'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${backendImage}'
      alwaysOn: true
      healthCheckPath: '/api/health/liveness'
      appSettings: [
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: dockerRegistryUrl
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_USERNAME'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=GHCR-USERNAME)'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_PASSWORD'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=GHCR-TOKEN)'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        // Key Vault references — the app's managed identity
        // must have "Get" permission on the vault.
        {
          name: 'DATABASE_URL'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=DATABASE-URL)'
        }
        {
          name: 'AZURE_STORAGE_CONNECTION_STRING'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=AZURE-STORAGE-CONNECTION-STRING)'
        }
        {
          name: 'BACKEND_SECRET'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=BACKEND-SECRET)'
        }
        {
          name: 'CORS_ORIGINS'
          value: 'https://${frontendAppName}.azurewebsites.net'
        }
      ]
    }
  }
}

// ── Frontend Web App ─────────────────────────

resource frontendApp 'Microsoft.Web/sites@2023-12-01' = {
  name: frontendAppName
  location: location
  kind: 'app,linux,container'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${frontendImage}'
      alwaysOn: true
      healthCheckPath: '/'
      appSettings: [
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: dockerRegistryUrl
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_USERNAME'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=GHCR-USERNAME)'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_PASSWORD'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=GHCR-TOKEN)'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        {
          name: 'BACKEND_URL'
          value: 'https://${backendApp.properties.defaultHostName}'
        }
        {
          name: 'AUTH_TRUST_HOST'
          value: 'true'
        }
        // Key Vault references for NextAuth secrets
        {
          name: 'AUTH_SECRET'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=AUTH-SECRET)'
        }
        {
          name: 'AUTH_GOOGLE_ID'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=AUTH-GOOGLE-ID)'
        }
        {
          name: 'AUTH_GOOGLE_SECRET'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=AUTH-GOOGLE-SECRET)'
        }
        {
          name: 'BACKEND_SECRET'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=BACKEND-SECRET)'
        }
      ]
    }
  }
}

// ── Outputs ──────────────────────────────────

@description('Backend Web App default hostname.')
output backendHostname string = backendApp.properties.defaultHostName

@description('Frontend Web App default hostname.')
output frontendHostname string = frontendApp.properties.defaultHostName

@description('Backend managed identity principal ID (for Key Vault access policies).')
output backendPrincipalId string = backendApp.identity.principalId

@description('Frontend managed identity principal ID (for Key Vault access policies).')
output frontendPrincipalId string = frontendApp.identity.principalId
