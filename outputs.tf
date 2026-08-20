output "instance_id" {
  description = "OCID of the compute instance"
  value       = oci_core_instance.main_instance.id
}

output "public_ip" {
  description = "Reserved Static Public IPv4 Address"
  value       = oci_core_public_ip.reserved_ip.ip_address
}

output "ssh_command" {
  description = "Command to SSH into the instance"
  value       = "ssh -i ~/.ssh/id_ed25519 opc@${oci_core_public_ip.reserved_ip.ip_address}"
}

output "vietcalendar_https_url" {
  description = "VietCalendar API & Swagger UI URL"
  value       = "https://${var.duckdns_domain}"
}

output "adguard_https_url" {
  description = "AdGuard Home Web Dashboard URL"
  value       = "https://adguard.${var.duckdns_domain}"
}

output "navidrome_https_url" {
  description = "Navidrome Lossless Music Server URL"
  value       = "https://music.${var.duckdns_domain}"
}

output "filebrowser_https_url" {
  description = "FileBrowser Personal Cloud Storage URL"
  value       = "https://files.${var.duckdns_domain}"
}

output "mcp_endpoint_url" {
  description = "Universal MCP Endpoint for AI clients"
  value       = "https://${var.duckdns_domain}/mcp/sse"
}
