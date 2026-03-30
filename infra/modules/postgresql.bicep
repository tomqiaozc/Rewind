// ──────────────────────────────────────────────
// Module: postgresql.bicep
// Provisions Azure Database for PostgreSQL
// Flexible Server (version 16) for the Rewind
// platform.
// ──────────────────────────────────────────────

@description('Name of the PostgreSQL Flexible Server.')
param serverName string

@description('Azure region for all resources.')
param location string

@description('Administrator login name.')
param administratorLogin string

@secure()
@description('Administrator login password. Stored securely — never logged.')
param administratorLoginPassword string

@description('PostgreSQL SKU tier. Use "Burstable" for dev, "GeneralPurpose" for prod.')
@allowed([
  'Burstable'
  'GeneralPurpose'
  'MemoryOptimized'
])
param skuTier string = 'Burstable'

@description('PostgreSQL SKU name (e.g. Standard_B1ms, Standard_D2ds_v4).')
param skuName string = 'Standard_B1ms'

@description('Storage size in GB.')
param storageSizeGB int = 32

// ── PostgreSQL Flexible Server ───────────────

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: serverName
  location: location
  sku: {
    name: skuName
    tier: skuTier
  }
  properties: {
    version: '16'
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorLoginPassword
    storage: {
      storageSizeGB: storageSizeGB
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

// ── Firewall: Allow Azure Services ───────────
// Setting start and end IP to 0.0.0.0 allows
// connections from other Azure services.

resource allowAzureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: postgresServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// ── Database ────────────────────────────────

resource rewindDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgresServer
  name: 'rewind'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// ── Outputs ──────────────────────────────────

@description('Fully qualified domain name of the PostgreSQL server.')
output serverFqdn string = postgresServer.properties.fullyQualifiedDomainName

@description('PostgreSQL connection string (password placeholder — replace at runtime).')
output connectionString string = 'postgresql://${administratorLogin}:PASSWORD@${postgresServer.properties.fullyQualifiedDomainName}:5432/rewind?sslmode=require'
