# Multi-Cloud Dynamic Auto-scaling Infrastructure Configuration

resource "aws_autoscaling_group" "finops_aws_asg" {
  name                = "finops-aws-autoscaling-group"
  max_size            = 10
  min_size            = 1
  desired_capacity    = 2
  vpc_zone_identifier = ["subnet-0123456789abcdef0"]

  mixed_instances_policy {
    instances_distribution {
      on_demand_base_capacity                  = 1
      on_demand_percentage_above_base_capacity = 20
      spot_allocation_strategy                 = "capacity-optimized"
    }

    launch_template {
      launch_template_specification {
        launch_template_id = "lt-0123456789abcdef0"
        version            = "$Latest"
      }
    }
  }
}

resource "google_compute_instance_group_manager" "finops_gcp_mig" {
  name               = "finops-gcp-managed-instance-group"
  base_instance_name = "finops-worker"
  zone               = "us-central1-a"
  target_size        = 2

  version {
    instance_template = "projects/your-gcp-project/global/instanceTemplates/finops-template"
  }
}

resource "azurerm_virtual_machine_scale_set" "finops_azure_vmss" {
  name                = "finops-azure-scale-set"
  location            = "East US"
  resource_group_name = "rg-finops-production"
  upgrade_policy_mode = "Manual"

  sku {
    name     = "Standard_B2s"
    tier     = "Standard"
    capacity = 2
  }

  os_profile {
    computer_name_prefix = "finops-vm"
    admin_username       = "finopsadmin"
    admin_password       = "P@ssw0rd1234!"
  }
}
