# Multi-Cloud FinOps Log Storage Infrastructure (AWS, GCP, Azure)

terraform {
  required_version = ">= 1.3.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  # Uncomment for collaborative, locked remote state:
  # backend "s3" {
  #   bucket         = var.state_bucket
  #   key            = "finops/terraform.tfstate"
  #   region         = var.state_region
  #   encrypt        = true
  #   dynamodb_table = "terraform-lock"
  # }
}

provider "aws" {
  region = var.region
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

provider "azurerm" {
  features {}
}

# AWS FinOps Telemetry Bucket
resource "aws_s3_bucket" "finops_logs" {
  bucket        = var.bucket_name
  force_destroy = false

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

resource "aws_s3_bucket_versioning" "finops_logs_versioning" {
  bucket = aws_s3_bucket.finops_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

# GCP FinOps BigQuery Export Storage Bucket
resource "google_storage_bucket" "finops_gcs" {
  name          = var.gcs_bucket_name
  location      = var.gcp_region
  storage_class = "STANDARD"
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

# Azure Cost Management Export Storage Account
resource "azurerm_resource_group" "finops_rg" {
  name     = "${var.azure_resource_group}-${var.environment}"
  location = var.azure_location
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