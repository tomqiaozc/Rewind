// ──────────────────────────────────────────────
// Module: keyvault.bicep
// Provisions Azure Key Vault with access
// policies for App Service managed identities
// and placeholder secrets for the Rewind
// platform.
// ──────────────────────────────────────────────

@description('Name of the Key Vault.')
param vaultName string

@description('Azure region for all resources.')
param location string

@description('Principal ID of the backend App Service managed identity.')
param backendPrincipalId string

@description('Principal ID of the frontend App Service managed identity.')
param frontendPrincipalId string

// ── Key Vault ────────────────────────────────

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: vaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enabledForDeployment: false
    enabledForTemplateDeployment: true
    enabledForDiskEncryption: false
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    accessPolicies: [
      // Backend App Service — can read secrets
      {
        tenantId: subscription().tenantId
        objectId: backendPrincipalId
        permissions: {
          secrets: [
            'get'
          ]
        }
      }
      // Frontend App Service — can read secrets
      {
        tenantId: subscription().tenantId
        objectId: frontendPrincipalId
        permissions: {
          secrets: [
            'get'
          ]
        }
      }
    ]
  }
}

// ── Placeholder Secrets ──────────────────────
// These are created with empty values. Actual
// secret values must be set manually (or via a
// deployment script) after initial provisioning.

resource secretAuthSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'AUTH-SECRET'
  properties: {
    value: 'REPLACE_ME'
  }
}

resource secretBackendSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'BACKEND-SECRET'
  properties: {
    value: 'REPLACE_ME'
  }
}

resource secretDatabaseUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'DATABASE-URL'
  properties: {
    value: 'REPLACE_ME'
  }
}

resource secretStorageConnectionString 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'AZURE-STORAGE-CONNECTION-STRING'
  properties: {
    value: 'REPLACE_ME'
  }
}

resource secretGoogleId 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'AUTH-GOOGLE-ID'
  properties: {
    value: 'REPLACE_ME'
  }
}

resource secretGoogleSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'AUTH-GOOGLE-SECRET'
  properties: {
    value: 'REPLACE_ME'
  }
}

// ── Outputs ──────────────────────────────────

@description('Key Vault URI.')
output vaultUri string = keyVault.properties.vaultUri

@description('Key Vault name.')
output vaultName string = keyVault.name
