// ──────────────────────────────────────────────
// Module: monitoring.bicep
// Provisions Log Analytics Workspace and
// Application Insights for the Rewind platform.
// ──────────────────────────────────────────────

@description('Name of the Log Analytics workspace.')
param workspaceName string

@description('Name of the Application Insights resource.')
param appInsightsName string

@description('Azure region for all resources.')
param location string

// ── Log Analytics Workspace ──────────────────

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// ── Application Insights ─────────────────────

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    IngestionMode: 'LogAnalytics'
  }
}

// ── Outputs ──────────────────────────────────

@description('Application Insights instrumentation key.')
output instrumentationKey string = appInsights.properties.InstrumentationKey

@description('Application Insights connection string.')
output connectionString string = appInsights.properties.ConnectionString

@description('Log Analytics workspace resource ID.')
output workspaceId string = logAnalytics.id
