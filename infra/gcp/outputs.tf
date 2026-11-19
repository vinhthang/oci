output "gce10_instance_id" {
  description = "GCP instance ID for gce10"
  value       = google_compute_instance.gce10.instance_id
}

output "gce10_self_link" {
  description = "Self link of the gce10 Compute Engine instance"
  value       = google_compute_instance.gce10.self_link
}

output "gce10_public_ip" {
  description = "Reserved static external IPv4 address for gce10"
  value       = google_compute_address.gce10_static_ip.address
}

output "gce10_ssh_command" {
  description = "SSH command to connect to gce10"
  value       = "ssh -i ~/.ssh/id_ed25519 opc@${google_compute_address.gce10_static_ip.address}"
}
