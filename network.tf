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

  # Ingress: WireGuard Mesh VPN (51820)
  ingress_security_rules {
    protocol    = "17" # UDP
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    description = "WireGuard Mesh VPN 51820"

    udp_options {
      min = 51820
      max = 51820
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
