// ──────────────────────────────────────────────
// Module: storage.bicep
// Provisions Azure Storage Account with a
// "sessions" blob container for the Rewind
// platform.
// ──────────────────────────────────────────────

@description('Name of the Storage Account (3-24 lowercase alphanumeric).')
@minLength(3)
@maxLength(24)
param storageAccountName string

@description('Azure region for all resources.')
param location string

// ── Storage Account ──────────────────────────

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

// ── Blob Services ────────────────────────────

resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

// ── Sessions Container ───────────────────────

resource sessionsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobServices
  name: 'sessions'
  properties: {
    publicAccess: 'None'
  }
}

// ── Outputs ──────────────────────────────────

@description('Storage account connection string.')
output connectionString string = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'

@description('Storage account name.')
output accountName string = storageAccount.name
