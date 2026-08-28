# ==============================================================================
# Hybrid Cloud & External Node Integration: oracle10 (32 GB RAM Powerhouse)
# ==============================================================================

# 1. Setup Tailscale & Update K3s TLS SAN on arm10 (Control Plane)
resource "null_resource" "arm10_tailscale_setup" {
  connection {
    type         = "ssh"
    user         = "opc"
    host         = oci_core_instance.arm10.private_ip
    bastion_host = oci_core_public_ip.reserved_ip.ip_address
    private_key  = file("~/.ssh/id_ed25519")
  }

  provisioner "remote-exec" {
    inline = [
      "which tailscale >/dev/null 2>&1 || (curl -fsSL https://tailscale.com/install.sh | sh)",
      "sudo tailscale up --accept-dns=false || true",
      "ARM_TS_IP=$(tailscale ip -4 2>/dev/null || echo '')",
      "if [ -n \"$ARM_TS_IP\" ]; then if ! grep -q \"$ARM_TS_IP\" /etc/systemd/system/k3s.service; then sudo sed -i \"/--tls-san/a \\    '--tls-san' '$ARM_TS_IP' \\\\\" /etc/systemd/system/k3s.service && sudo systemctl daemon-reload && sudo systemctl restart k3s; fi; fi"
    ]
  }
}

# 2. Join oracle10 to K3s Cluster over Tailscale Interface (Zero-Touch Tailscale)
resource "null_resource" "oracle10_k3s_join" {
  depends_on = [null_resource.arm10_tailscale_setup]

  connection {
    type        = "ssh"
    user        = "thang"
    host        = "oracle10"
    private_key = file("~/.ssh/id_ed25519")
  }

  provisioner "remote-exec" {
    inline = [
      "echo '=== Preparing oracle10 for K3s Agent ==='",
      "sudo modprobe br_netfilter || true",
      "sudo modprobe overlay || true",
      "ORACLE_TS_IP=$(tailscale ip -4)",
      "echo \"oracle10 Tailscale IP: $ORACLE_TS_IP\""
    ]
  }
}
