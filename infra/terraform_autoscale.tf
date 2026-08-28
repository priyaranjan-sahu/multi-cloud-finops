# Multi-Cloud Dynamic Auto-scaling Infrastructure Configuration

# AWS Auto Scaling Group with a spot-mixed capacity strategy
resource "aws_autoscaling_group" "finops_aws_asg" {
  name               = "finops-aws-autoscaling-group"
  max_size           = var.asg_max_size
  min_size           = var.asg_min_size
  desired_capacity   = var.asg_min_size
  vpc_zone_identifier = var.vpc_zone_identifier

  mixed_instances_policy {
    instances_distribution {
      on_demand_base_capacity                  = var.asg_min_size
      on_demand_percentage_above_base_capacity = 20
      spot_allocation_strategy                 = "capacity-optimized"
    }

    launch_template {
      launch_template_specification {
        launch_template_id = var.launch_template_id
        version            = "$Latest"
      }
    }
  }
}

# GCP Managed Instance Group
resource "google_compute_instance_group_manager" "finops_gcp_mig" {
  name               = "finops-gcp-managed-instance-group"
  base_instance_name = "finops-worker"
  zone               = "${var.gcp_region}-a"
  target_size        = var.asg_min_size

  version {
    instance_template = var.gcp_instance_template
  }
}

# Azure Virtual Machine Scale Set (SSH-key auth; no hardcoded passwords)
resource "azurerm_virtual_machine_scale_set" "finops_azure_vmss" {
  name                = "finops-azure-scale-set"
  location            = var.azure_location
  resource_group_name = azurerm_resource_group.finops_rg.name
  upgrade_policy_mode = "Manual"

  sku {
    name     = "Standard_B2s"
    tier     = "Standard"
    capacity = var.asg_min_size
  }

  os_profile {
    computer_name_prefix = "finops-vm"
    admin_username       = var.vmss_admin_username
  }

  os_profile_linux_config {
    disable_password_authentication = true

    ssh_keys {
      path     = "/home/${var.vmss_admin_username}/.ssh/authorized_keys"
      key_data = var.vmss_admin_ssh_public_key
    }
  }
}