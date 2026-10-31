# 1. Fetch Availability Domains
data "oci_identity_availability_domains" "ads" {
  compartment_id = local.compartment_id
}

# 2. Fetch Latest Oracle Linux 10 Images for AMD (x86_64) and ARM (aarch64)
data "oci_core_images" "oracle_linux_10_amd" {
  compartment_id           = local.compartment_id
  operating_system         = "Oracle Linux"
  operating_system_version = "10"
  shape                    = "VM.Standard.E2.1.Micro"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

data "oci_core_images" "oracle_linux_10_arm" {
  compartment_id           = local.compartment_id
  operating_system         = "Oracle Linux"
  operating_system_version = "10"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# 3. Reserved Always Free Static Public IP (for amd10 Gateway)
resource "oci_core_public_ip" "reserved_ip" {
  compartment_id = local.compartment_id
  lifetime       = "RESERVED"
  display_name   = "static-ip-oracle-linux-10"
}

# 4. Render Cloud-Init user_data script using native templatefile function
locals {
  user_data = templatefile("${path.module}/cloud-init.sh.tpl", {
    domain_name = var.domain_name
  })
}

# ==============================================================================
# Node 1: amd10 (Frontend Gateway & Ingress - Reserved Public IP 152.70.101.162)
# ==============================================================================
resource "oci_core_instance" "amd10" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = local.compartment_id
  display_name        = "amd10"
  shape               = "VM.Standard.E2.1.Micro"

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.oracle_linux_10_amd.images[0].id
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public_subnet.id
    display_name     = "vnic-amd10"
    assign_public_ip = false # Using Reserved Static IP instead
    hostname_label   = "amd10"
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = base64encode(local.user_data)
  }

  preserve_boot_volume = false
}

# Bind Reserved Public IP to amd10 Primary Private IP
data "oci_core_vnic_attachments" "amd10_vnics" {
  compartment_id = local.compartment_id
  instance_id    = oci_core_instance.amd10.id
}

data "oci_core_private_ips" "amd10_private_ip" {
  vnic_id = data.oci_core_vnic_attachments.amd10_vnics.vnic_attachments[0].vnic_id
}

resource "null_resource" "bind_reserved_ip" {
  depends_on = [oci_core_instance.amd10]

  provisioner "local-exec" {
    command = "oci network public-ip update --public-ip-id ${oci_core_public_ip.reserved_ip.id} --private-ip-id ${data.oci_core_private_ips.amd10_private_ip.private_ips[0].id} --force 2>/dev/null || true"
  }
}

# ==============================================================================
# Node 2: amd11 (K3s Worker & Dedicated Storage / Navidrome / FileBrowser)
# ==============================================================================
resource "oci_core_instance" "amd11" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = local.compartment_id
  display_name        = "amd11"
  shape               = "VM.Standard.E2.1.Micro"

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.oracle_linux_10_amd.images[0].id
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.private_subnet.id
    display_name     = "vnic-amd11"
    assign_public_ip = false
    hostname_label   = "amd11"
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }

  preserve_boot_volume = false
}

# ==============================================================================
# Node 3: arm10 (K3s Master Powerhouse - 4 OCPUs, 24 GB RAM Ampere A1)
# ==============================================================================
resource "oci_core_instance" "arm10" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = local.compartment_id
  display_name        = "arm10"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = 4
    memory_in_gbs = 24
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.oracle_linux_10_arm.images[0].id
    boot_volume_size_in_gbs = 100
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.private_subnet.id
    display_name     = "vnic-arm10"
    assign_public_ip = false
    hostname_label   = "arm10"
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }

  preserve_boot_volume = false
}

# ==============================================================================
# Always Free PAYG Compartment Quota Guardrail ($0/month Hard Lock)
# ==============================================================================
resource "oci_limits_quota" "always_free_guardrail" {
  compartment_id = var.tenancy_ocid
  name           = "always-free-payg-guardrail"
  description    = "Hard lock on Compute A1 and Block Storage to prevent usage beyond OCI Always Free PAYG tier ($0/mo)"
  statements = [
    "set compute-core quota standard-a1-core-count to 4 in tenancy",
    "set compute-memory quota standard-a1-memory-count to 24 in tenancy",
    "set block-storage quota total-storage-gb to 200 in tenancy",
  ]
}
