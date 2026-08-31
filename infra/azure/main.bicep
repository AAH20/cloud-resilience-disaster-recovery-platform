targetScope = 'resourceGroup'
param location string = resourceGroup().location
param suffix string = uniqueString(subscription().subscriptionId, resourceGroup().id)

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'continuity-law-${suffix}'
  location: location
  properties: {retentionInDays: 30, features: {enableLogAccessUsingOnlyResourcePermissions: true}}
}

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'continuity-ai-${suffix}'
  location: location
  kind: 'web'
  properties: {Application_Type: 'web', WorkspaceResourceId: logs.id}
}

resource evidence 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: take('continuity${suffix}', 24)
  location: location
  sku: {name: 'Standard_GRS'}
  kind: 'StorageV2'
  properties: {minimumTlsVersion: 'TLS1_2', allowBlobPublicAccess: false, supportsHttpsTrafficOnly: true}
}

resource blob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {parent: evidence, name: 'default'}
resource receipts 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blob
  name: 'recovery-receipts'
  properties: {publicAccess: 'None', immutableStorageWithVersioning: {enabled: true}}
}

output applicationInsightsName string = insights.name
output logAnalyticsName string = logs.name
output evidenceStorageName string = evidence.name
