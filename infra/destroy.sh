#!/usr/bin/env bash
set -euo pipefail

# Destroys the Multi-Cloud FinOps infrastructure for the current workspace.
# Usage: ./destroy.sh [workspace]

WORKSPACE="${1:-production}"

echo "==> Destroying Multi-Cloud FinOps Infrastructure (workspace: ${WORKSPACE})"

terraform init -upgrade
terraform workspace select "${WORKSPACE}"

# Fail loudly if this is a shared production environment.
if [[ "${WORKSPACE}" == "production" ]]; then
  read -r -p "Are you sure you want to destroy PRODUCTION infrastructure? (yes/no) " confirm
  if [[ "${confirm}" != "yes" ]]; then
    echo "Aborted."
    exit 1
  fi
fi

terraform destroy -auto-approve

echo "Infrastructure destroyed!"