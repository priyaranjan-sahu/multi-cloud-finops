# Input variables for the Multi-Cloud FinOps infrastructure.
# Provide real values via terraform.tfvars (see terraform.tfvars.example).

variable "environment" {
  type        = string
  description = "Deployment environment (dev, staging, production)."
  default     = "production"
}

variable "region" {
  type        = string
  description = "AWS region for FinOps resources."
  default     = "us-east-1"
}

variable "gcp_project" {
  type        = string
  description = "GCP project ID for FinOps resources."
  default     = "your-gcp-project"
}

variable "gcp_region" {
  type        = string
  description = "GCP region for FinOps resources."
  default     = "us-central1"
}

variable "azure_location" {
  type        = string
  description = "Azure region for FinOps resources."
  default     = "East US"
}

variable "bucket_name" {
  type        = string
  description = "Globally unique name for the AWS FinOps telemetry bucket."
  default     = "multi-cloud-finops-telemetry-000000"
}

variable "gcs_bucket_name" {
  type        = string
  description = "Globally unique name for the GCP billing export bucket."
  default     = "multi-cloud-finops-gcs-billing"
}

variable "azure_resource_group" {
  type        = string
  description = "Name of the Azure resource group for FinOps storage."
  default     = "rg-finops"
}

variable "vpc_zone_identifier" {
  type        = list(string)
  description = "Subnet IDs for the AWS Auto Scaling Group. Required before apply."
  default     = []
}

variable "launch_template_id" {
  type        = string
  description = "Launch template ID for the AWS Auto Scaling Group. Required before apply."
  default     = ""
}

variable "gcp_instance_template" {
  type        = string
  description = "Fully-qualified GCP instance template reference for the managed instance group."
  default     = ""
}

variable "asg_min_size" {
  type        = number
  description = "Minimum number of instances in the AWS Auto Scaling Group."
  default     = 1
}

variable "asg_max_size" {
  type        = number
  description = "Maximum number of instances in the AWS Auto Scaling Group."
  default     = 10
}

variable "vmss_admin_username" {
  type        = string
  description = "Admin username for the Azure scale set instances."
  default     = "finopsadmin"
}

variable "vmss_admin_ssh_public_key" {
  type        = string
  description = "SSH public key for the Azure scale set instances. Leave empty to skip auth config."
  default     = ""
}

# Remote state backend (uncomment the backend block in terraform.tf and fill these).
variable "state_bucket" {
  type        = string
  description = "S3 bucket for remote Terraform state. Only used if backend is enabled."
  default     = ""
}

variable "state_region" {
  type        = string
  description = "Region for the remote state bucket. Only used if backend is enabled."
  default     = "us-east-1"
}