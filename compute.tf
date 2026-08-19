# 1. Fetch Availability Domains
data "oci_identity_availability_domains" "ads" {
  compartment_id = local.compartment_id
}

# 2. Fetch Latest Oracle Linux 10 Image
data "oci_core_images" "oracle_linux_10" {
  compartment_id           = local.compartment_id
  operating_system         = "Oracle Linux"
  operating_system_version = "10"
  shape                    = var.instance_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# 3. Reserved Always Free Static Public IP
resource "oci_core_public_ip" "reserved_ip" {
  compartment_id = local.compartment_id
  lifetime       = "RESERVED"
  display_name   = "ip-vietcalendar-static"
}

# 4. Render Cloud-Init user_data script
data "template_file" "user_data" {
  template = file("${path.module}/cloud-init.sh.tpl")
  vars = {
    duckdns_domain = var.duckdns_domain
  }
}

# 5. Compute Instance
resource "oci_core_instance" "main_instance" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = local.compartment_id
  display_name        = "instance-oracle-linux-10"
  shape               = var.instance_shape

  dynamic "shape_config" {
    for_each = var.instance_shape == "VM.Standard.A1.Flex" ? [1] : []
    content {
      ocpus         = 4
      memory_in_gbs = 24
    }
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.oracle_linux_10.images[0].id
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public_subnet.id
    display_name     = "vnic-primary"
    assign_public_ip = false # Using our Reserved Static IP instead
    hostname_label   = "vietcalendar"
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = base64encode(data.template_file.user_data.rendered)
  }

  preserve_boot_volume = false
}

# 6. Bind Reserved Public IP to the Instance's Primary Private IP
data "oci_core_vnic_attachments" "instance_vnics" {
  compartment_id = local.compartment_id
  instance_id    = oci_core_instance.main_instance.id
}

data "oci_core_private_ips" "primary_private_ip" {
  vnic_id = data.oci_core_vnic_attachments.instance_vnics.vnic_attachments[0].vnic_id
}

# Associate reserved public IP
resource "null_resource" "bind_reserved_ip" {
  depends_on = [oci_core_instance.main_instance]

  provisioner "local-exec" {
    command = "oci network public-ip update --public-ip-id ${oci_core_public_ip.reserved_ip.id} --private-ip-id ${data.oci_core_private_ips.primary_private_ip.private_ips[0].id} --force 2>/dev/null || true"
  }
}
