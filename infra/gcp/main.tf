# ==============================================================================
# Reserved External Static IP for gce10 (US-Central Edge & Worker)
# ==============================================================================
resource "google_compute_address" "gce10_static_ip" {
  name         = "gce10-static-ip"
  region       = var.region
  address_type = "EXTERNAL"
  network_tier = "STANDARD"
  address      = var.static_ip_address
}

# ==============================================================================
# Firewall Rules: Edge HTTP/HTTPS (80/443) and WireGuard VPN (51820/UDP)
# ==============================================================================
resource "google_compute_firewall" "gce10_http_https" {
  name    = "gce10-allow-http-https"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["gce10-edge"]
}

resource "google_compute_firewall" "gce10_wireguard" {
  name    = "gce10-allow-wireguard"
  network = "default"

  allow {
    protocol = "udp"
    ports    = ["51820"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["gce10-edge"]
}

# ==============================================================================
# Node 4: gce10 (GCP Always Free e2-micro - Oracle Linux 10)
# ==============================================================================
resource "google_compute_instance" "gce10" {
  name                = "gce-free-vm"
  machine_type        = "e2-micro"
  zone                = var.zone
  deletion_protection = true

  tags = ["http-server", "https-server"]

  boot_disk {
    auto_delete = false

    initialize_params {
      image = "oracle-linux-cloud/oracle-linux-10"
      size  = 30
      type  = "pd-standard"
    }
  }

  network_interface {
    network = "default"

    access_config {
      nat_ip       = google_compute_address.gce10_static_ip.address
      network_tier = "STANDARD"
    }
  }

  metadata = {
    ssh-keys = "opc:${var.ssh_public_key}"
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      boot_disk[0].initialize_params[0].image,
      metadata,
    ]
  }
}
