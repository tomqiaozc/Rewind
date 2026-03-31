// ──────────────────────────────────────────────
// Module: keyvault.bicep
// Provisions Azure Key Vault with access
// policies for App Service managed identities.
//
// IMPORTANT: Secrets are NOT managed by Bicep.
// They must be set via Azure CLI after initial
// provisioning to avoid overwriting real values
// on redeployment. Required secrets:
//
//   az keyvault secret set --vault-name <name> --name <SECRET> --value <value>
//
//   AUTH-SECRET                      (openssl rand -base64 32)
//   BACKEND-SECRET                   (openssl rand -base64 32)
//   DATABASE-URL                     (postgresql+asyncpg://...)
//   AZURE-STORAGE-CONNECTION-STRING  (from Azure portal)
//   AUTH-GOOGLE-ID                   (Google Cloud Console)
//   AUTH-GOOGLE-SECRET               (Google Cloud Console)
//   GHCR-USERNAME                    (GitHub username)
//   GHCR-TOKEN                       (GitHub PAT with packages:read)
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

// ── Outputs ──────────────────────────────────

@description('Key Vault URI.')
output vaultUri string = keyVault.properties.vaultUri

@description('Key Vault name.')
output vaultName string = keyVault.name
