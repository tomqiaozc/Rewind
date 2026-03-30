using '../main.bicep'

param environment = 'prod'
param projectName = 'rwnd'
param location = 'eastasia'
param postgresAdminPassword = readEnvironmentVariable('PG_PASS', '')
