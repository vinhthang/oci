# OCI Always Free Infrastructure (Terraform & OCI CLI)

Automated, production-ready infrastructure code for provisioning a complete **Oracle Cloud Always Free** server with:

* 🛡️ **AdGuard Home**: Network-wide DNS ad & tracker blocker with DNS-over-TLS (DoT).
* 📅 **VietCalendar**: High-performance Rust Axum REST API and Universal MCP Server for AI assistants.
* 🔒 **Caddy Web Server**: Automated Let's Encrypt SSL/TLS reverse proxy for DuckDNS domains.
* ⚡ **Kernel & Memory Tuning**: Automated 2.5 GB swap file setup and `crashkernel` RAM reclamation.

---

## 📁 Repository Structure

```text
├── provider.tf              # OCI Terraform provider settings
├── variables.tf             # Input variables & customizable parameters
├── network.tf               # VCN, Subnet, Internet Gateway & Security List rules
├── compute.tf               # Compute instance, Reserved Static IP & VNIC attachment
├── cloud-init.sh.tpl        # Automated post-boot provisioning script
├── outputs.tf               # Public IP, SSH command, and HTTPS URLs
├── terraform.tfvars.example # Sample variable definitions file
└── docs/
    └── oci-cli-guide.md     # Complete OCI CLI commands reference guide
```

---

## 🚀 Deployment Option 1: Terraform (Recommended)

### 1. Configure Variables
```bash
cp terraform.tfvars.example terraform.tfvars
```
Edit `terraform.tfvars` with your Tenancy OCID and SSH Public Key (`cat ~/.ssh/id_ed25519.pub`).

### 2. Plan & Apply
```bash
terraform init
terraform plan
terraform apply
```

---

## 💻 Deployment Option 2: OCI CLI (Direct Terminal Commands)

For a complete manual runbook using the official **OCI CLI** (creating VCN, Subnet, Security List, Reserved Static IP, and Launching the Instance), see:

👉 **[docs/oci-cli-guide.md](docs/oci-cli-guide.md)**

### Quick OCI CLI Instance Launch Snippet:
```bash
oci compute instance launch \
  --compartment-id <TENANCY_OCID> \
  --availability-domain "tTNg:AP-TOKYO-1-AD-1" \
  --shape "VM.Standard.E2.1.Micro" \
  --display-name "instance-oracle-linux-10" \
  --image-id "ocid1.image.oc1.ap-tokyo-1.aaaaaaaahgh5scxcd7whdaf3j6e73julskgpwts67ttbrn4mkr72x3bce5fa" \
  --subnet-id <SUBNET_OCID> \
  --assign-public-ip false \
  --ssh-authorized-keys-file ~/.ssh/id_ed25519.pub \
  --user-data-file cloud-init.sh.tpl
```

---

## 🌐 Endpoints Created

* **VietCalendar & MCP Server**: `https://<your-domain>.duckdns.org`
* **Swagger UI**: `https://<your-domain>.duckdns.org/swagger-ui/`
* **AdGuard Home Dashboard**: `https://adguard.<your-domain>.duckdns.org`
* **Navidrome Music Server**: `https://music.<your-domain>.duckdns.org`
* **Android Private DNS (DoT)**: `<your-domain>.duckdns.org` (Port 853)
