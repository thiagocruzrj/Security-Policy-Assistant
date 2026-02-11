terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "stterraformstate001"
    container_name       = "tfstate"
    key                  = "security-policy-assistant/dev.tfstate"
  }
}

provider "azurerm" {
  features {}
}

# ──────────────────── Variables ────────────────────
variable "project_name" {
  default = "sectbot"
}
variable "environment" {
  default = "dev"
}
variable "location" {
  default = "eastus"
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags = {
    project     = "security-policy-assistant"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ──────────────────── Resource Group ────────────────────
resource "azurerm_resource_group" "main" {
  name     = "rg-${local.name_prefix}"
  location = var.location
  tags     = local.tags
}

# ──────────────────── Storage Account ────────────────────
resource "azurerm_storage_account" "main" {
  name                     = "st${var.project_name}${var.environment}001"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = local.tags
}

resource "azurerm_storage_container" "policy_docs" {
  name                  = "policy-docs"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# ──────────────────── Azure AI Search ────────────────────
resource "azurerm_search_service" "main" {
  name                = "search-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "basic" # Required for Semantic Ranker
  tags                = local.tags
}

# ──────────────────── Key Vault ────────────────────
resource "azurerm_key_vault" "main" {
  name                       = "kv-${local.name_prefix}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
  tags                       = local.tags
}

data "azurerm_client_config" "current" {}

# ──────────────────── Log Analytics ────────────────────
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 90
  tags                = local.tags
}

resource "azurerm_application_insights" "main" {
  name                = "appi-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = local.tags
}

# ──────────────────── Outputs ────────────────────
output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "storage_account_name" {
  value = azurerm_storage_account.main.name
}

output "search_service_name" {
  value = azurerm_search_service.main.name
}

output "app_insights_connection_string" {
  value     = azurerm_application_insights.main.connection_string
  sensitive = true
}
