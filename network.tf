locals {
  compartment_id = var.compartment_ocid != "" ? var.compartment_ocid : var.tenancy_ocid
}

# 1. Virtual Cloud Network (VCN)
resource "oci_core_vcn" "main_vcn" {
  compartment_id = local.compartment_id
  cidr_block     = "10.0.0.0/16"
  display_name   = "vcn-vietcalendar"
  dns_label      = "vietcalendar"
}

# 2. Internet Gateway
resource "oci_core_internet_gateway" "main_igw" {
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.main_vcn.id
  display_name   = "igw-vietcalendar"
  enabled        = true
}

# 3. Route Table
resource "oci_core_default_route_table" "default_route_table" {
  manage_default_resource_id = oci_core_vcn.main_vcn.default_route_table_id

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.main_igw.id
  }
}

# 4. Security List
resource "oci_core_security_list" "main_security_list" {
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.main_vcn.id
  display_name   = "seclist-vietcalendar"

  # All outbound traffic allowed
  egress_security_rules {
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    protocol         = "all"
    stateless        = false
  }

  # Ingress: SSH (22)
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    description = "SSH"

    tcp_options {
      min = 22
      max = 22
    }
  }

  # Ingress: HTTP (80)
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    description = "HTTP 80"

    tcp_options {
      min = 80
      max = 80
    }
  }

  # Ingress: HTTPS (443)
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    description = "HTTPS 443"

    tcp_options {
      min = 443
      max = 443
    }
  }

  # Ingress: VietCalendar Port (8080)
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    description = "VietCalendar API 8080"

    tcp_options {
      min = 8080
      max = 8080
    }
  }

  # Ingress: DNS UDP (53)
  ingress_security_rules {
    protocol    = "17" # UDP
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    description = "DNS UDP 53"

    udp_options {
      min = 53
      max = 53
    }
  }

  # Ingress: DNS TCP (53)
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    description = "DNS TCP 53"

    tcp_options {
      min = 53
      max = 53
    }
  }

  # Ingress: DNS-over-TLS (853)
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    description = "AdGuard DoT 853"

    tcp_options {
      min = 853
      max = 853
    }
  }

  # Ingress: AdGuard Setup UI (3000)
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    description = "AdGuard Setup 3000"

    tcp_options {
      min = 3000
      max = 3000
    }
  }

  # Ingress: AdGuard Web / DoH (8443)
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    description = "AdGuard Web / DoH 8443"

    tcp_options {
      min = 8443
      max = 8443
    }
  }

  # Ingress: ICMP (Ping & Path MTU)
  ingress_security_rules {
    protocol    = "1" # ICMP
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false

    icmp_options {
      type = 3
      code = 4
    }
  }


  # Ingress: K3s Kubernetes API (6443)
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "10.0.0.0/16"
    source_type = "CIDR_BLOCK"
    stateless   = false
    description = "K3s Kubernetes API (Internal VCN) 6443"

    tcp_options {
      min = 6443
      max = 6443
    }
  }

  # Ingress: Internal Subnet Traffic
  ingress_security_rules {
    protocol    = "all"
    source      = "10.0.0.0/16"
    source_type = "CIDR_BLOCK"
    stateless   = false
    description = "Internal VCN traffic"
  }
}

# 5. Public Subnet
resource "oci_core_subnet" "public_subnet" {
  compartment_id             = local.compartment_id
  vcn_id                     = oci_core_vcn.main_vcn.id
  cidr_block                 = "10.0.0.0/24"
  display_name               = "subnet-vcn-vietcalendar"
  dns_label                  = "public"
  security_list_ids          = [oci_core_security_list.main_security_list.id]
  prohibit_public_ip_on_vnic = false
}

# 6. OCI NAT Gateway (Always Free • Outbound Egress Only)
resource "oci_core_nat_gateway" "main_nat_gateway" {
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.main_vcn.id
  display_name   = "nat-gateway-vietcalendar"
}

# 7. OCI Service Gateway (Direct access to Oracle Cloud Services Network)
data "oci_core_services" "all_services" {
  filter {
    name   = "name"
    values = ["All .* Services In Oracle Services Network"]
    regex  = true
  }
}

resource "oci_core_service_gateway" "main_service_gateway" {
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.main_vcn.id
  display_name   = "service-gateway-vietcalendar"
  services {
    service_id = data.oci_core_services.all_services.services[0].id
  }
}

# 8. Private Route Table
resource "oci_core_route_table" "private_route_table" {
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.main_vcn.id
  display_name   = "routetable-private-vietcalendar"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_nat_gateway.main_nat_gateway.id
    description       = "Default internet egress via NAT Gateway"
  }

  route_rules {
    destination       = data.oci_core_services.all_services.services[0].cidr_block
    destination_type  = "SERVICE_CIDR_BLOCK"
    network_entity_id = oci_core_service_gateway.main_service_gateway.id
    description       = "Oracle Services Network traffic via Service Gateway"
  }
}

# 9. Private Security List
resource "oci_core_security_list" "private_security_list" {
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.main_vcn.id
  display_name   = "seclist-private-vietcalendar"

  # All outbound traffic allowed via NAT Gateway
  egress_security_rules {
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    protocol         = "all"
    stateless        = false
    description      = "Allow all outbound internet traffic via NAT Gateway"
  }

  # Ingress: Allow all intra-VCN traffic from Public Subnet (amd10) and cluster nodes
  ingress_security_rules {
    protocol    = "all"
    source      = "10.0.0.0/16"
    source_type = "CIDR_BLOCK"
    stateless   = false
    description = "Allow all internal VCN traffic (K3s, SSH ProxyJump, Caddy proxy)"
  }
}

# 10. Private Subnet (Strictly isolated from public internet ingress)
resource "oci_core_subnet" "private_subnet" {
  compartment_id             = local.compartment_id
  vcn_id                     = oci_core_vcn.main_vcn.id
  cidr_block                 = "10.0.1.0/24"
  display_name               = "subnet-private-vietcalendar"
  dns_label                  = "private"
  route_table_id             = oci_core_route_table.private_route_table.id
  security_list_ids          = [oci_core_security_list.private_security_list.id]
  prohibit_public_ip_on_vnic = true
  prohibit_internet_ingress  = true
}

