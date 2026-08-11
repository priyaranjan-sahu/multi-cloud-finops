# Multi-Cloud FinOps Log Storage Infrastructure (AWS, GCP, Azure)

terraform {
  required_version = ">= 1.3.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

variable "environment" {
  type    = string
  default = "production"
}

# AWS FinOps Telemetry Bucket
resource "aws_s3_bucket" "finops_logs" {
  bucket        = "multi-cloud-finops-telemetry-bucket"
  force_destroy = true

  tags = {
    Environment = var.environment
    ManagedBy   = "FinOps-Framework"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "finops_s3_encryption" {
  bucket = aws_s3_bucket.finops_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# GCP FinOps BigQuery Export Storage Bucket
resource "google_storage_bucket" "finops_gcs" {
  name          = "multi-cloud-finops-gcs-billing"
  location      = "US"
  storage_class = "STANDARD"
  force_destroy = true

  uniform_bucket_level_access = true
}

# Azure Cost Management Export Storage Account
resource "azurerm_resource_group" "finops_rg" {
  name     = "rg-finops-production"
  location = "East US"
}

resource "azurerm_storage_account" "finops_azure_sa" {
  name                     = "finopsstorageacct"
  resource_group_name      = azurerm_resource_group.finops_rg.name
  location                 = azurerm_resource_group.finops_rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  tags = {
    Environment = var.environment
    ManagedBy   = "FinOps-Framework"
  }
}

output "aws_finops_s3_bucket" {
  value = aws_s3_bucket.finops_logs.id
}

output "gcp_finops_storage_bucket" {
  value = google_storage_bucket.finops_gcs.id
}

output "azure_finops_storage_account" {
  value = azurerm_storage_account.finops_azure_sa.name
}
