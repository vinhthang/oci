# ==============================================================================
# Node 1: amd10 (Gateway) Outputs
# ==============================================================================
output "amd10_instance_id" {
  description = "OCID of amd10"
  value       = oci_core_instance.amd10.id
}

output "amd10_public_ip" {
  description = "Reserved Static Public IPv4 Address for amd10"
  value       = oci_core_public_ip.reserved_ip.ip_address
}

output "amd10_ssh_command" {
  description = "SSH Command to connect to amd10"
  value       = "ssh -i ~/.ssh/id_ed25519 opc@${oci_core_public_ip.reserved_ip.ip_address}"
}

# ==============================================================================
# Node 2: amd11 (Storage Node) Outputs
# ==============================================================================
output "amd11_instance_id" {
  description = "OCID of amd11"
  value       = oci_core_instance.amd11.id
}

output "amd11_ssh_command" {
  description = "SSH Command to connect to amd11 via ProxyJump"
  value       = "ssh -o ProxyJump=opc@${oci_core_public_ip.reserved_ip.ip_address} -i ~/.ssh/id_ed25519 opc@${oci_core_instance.amd11.private_ip}"
}

# ==============================================================================
# Node 3: arm10 (K3s Master Powerhouse - Private Subnet)
# ==============================================================================
output "arm10_instance_id" {
  description = "OCID of arm10"
  value       = oci_core_instance.arm10.id
}

output "arm10_ssh_command" {
  description = "SSH Command to connect to arm10 via Bastion ProxyJump"
  value       = "ssh -o ProxyJump=opc@${oci_core_public_ip.reserved_ip.ip_address} -i ~/.ssh/id_ed25519 opc@${oci_core_instance.arm10.private_ip}"
}

# ==============================================================================
# Service HTTPS Endpoints (Custom Domain: vinhthang.dev)
# ==============================================================================
output "blog_https_url" {
  description = "Hugo PaperMod Tech Blog URL"
  value       = "https://${var.domain_name}"
}

output "vietcalendar_https_url" {
  description = "VietCalendar API & Swagger UI URL"
  value       = "https://api.${var.domain_name}"
}

output "memos_https_url" {
  description = "Memos AI Digital Notebook URL"
  value       = "https://memos.${var.domain_name}"
}

output "anythingllm_https_url" {
  description = "AnythingLLM Document RAG & Agent URL"
  value       = "https://ai.${var.domain_name}"
}

output "navidrome_https_url" {
  description = "Navidrome Lossless Music Server URL"
  value       = "https://music.${var.domain_name}"
}

output "filebrowser_https_url" {
  description = "FileBrowser Personal Cloud Storage URL"
  value       = "https://files.${var.domain_name}"
}

output "adguard_https_url" {
  description = "AdGuard Home Web Dashboard URL"
  value       = "https://adguard.${var.domain_name}"
}
