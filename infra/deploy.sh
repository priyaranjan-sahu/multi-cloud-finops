#!/usr/bin/env bash
set -euo pipefail

# Deploys the Multi-Cloud FinOps infrastructure with Terraform.
# Usage: ./deploy.sh [workspace]

WORKSPACE="${1:-production}"
ENV_FILE=".terraform/environment"

echo "==> Deploying Multi-Cloud FinOps Infrastructure (workspace: ${WORKSPACE})"

# Initialize Terraform (downloads providers, configures backend)
terraform init -upgrade

# Create/select a dedicated workspace per environment
if [[ ! -f "${ENV_FILE}" || "$(cat "${ENV_FILE}")" != "${WORKSPACE}" ]]; then
  terraform workspace new "${WORKSPACE}" 2>/dev/null || terraform workspace select "${WORKSPACE}"
else
  terraform workspace select "${WORKSPACE}"
fi

# Validate and plan before touching anything
terraform validate
terraform plan -out="tfplan.${WORKSPACE}"

echo "==> Review the plan above, then apply with:"
echo "    terraform apply tfplan.${WORKSPACE}"