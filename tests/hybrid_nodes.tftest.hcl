# Unit Test Suite for Hybrid Node Integration

mock_provider "oci" {
  mock_data "oci_identity_availability_domains" {
    defaults = {
      availability_domains = [
        {
          name = "AD-1"
        }
      ]
    }
  }
  mock_data "oci_core_images" {
    defaults = {
      images = [
        {
          id = "ocid1.image.oc1..mock"
        }
      ]
    }
  }
  mock_data "oci_core_services" {
    defaults = {
      services = [
        {
          id = "ocid1.service.oc1..mock"
        }
      ]
    }
  }
  mock_data "oci_core_vnic_attachments" {
    defaults = {
      vnic_attachments = [
        {
          vnic_id = "ocid1.vnic.oc1..mock"
        }
      ]
    }
  }
  mock_data "oci_core_private_ips" {
    defaults = {
      private_ips = [
        {
          id = "ocid1.privateip.oc1..mock"
        }
      ]
    }
  }
}

variables {
  tenancy_ocid   = "ocid1.tenancy.oc1..mock"
  ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMockKey"
  domain_name    = "vinhthang.dev"
}

run "verify_hybrid_node_outputs" {
  command = plan

  assert {
    condition     = output.oracle10_node_name == "oracle10"
    error_message = "oracle10 node name output must be strictly 'oracle10'"
  }

  assert {
    condition     = output.oracle10_role == "worker-java-services"
    error_message = "oracle10 role output must be 'worker-java-services'"
  }
}
