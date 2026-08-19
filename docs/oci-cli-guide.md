# Provisioning Oracle Cloud Infrastructure via OCI CLI

This guide contains all the step-by-step **OCI CLI commands** to provision and configure the Always Free instance manually from the terminal.

---

## 📋 Prerequisites & Configuration

Ensure your `~/.oci/config` is configured with your Tenancy OCID, User OCID, Fingerprint, and Region (`ap-tokyo-1`):

```bash
# Verify authentication
oci os ns get
```

---

## 1. Discover Environment Information

```bash
# Set your tenancy variable
export COMPARTMENT_ID="ocid1.tenancy.oc1..your_tenancy_ocid_here"

# 1. Get Availability Domain
oci iam availability-domain list --compartment-id $COMPARTMENT_ID --query 'data[*].name' --output table

# 2. Get Latest Oracle Linux 10 Image OCID
oci compute image list \
  --compartment-id $COMPARTMENT_ID \
  --operating-system "Oracle Linux" \
  --operating-system-version "10" \
  --shape "VM.Standard.E2.1.Micro" \
  --query 'data[0].{Name:"display-name", OCID:id}' \
  --output table
```

---

## 2. Network Provisioning (VCN & Security List)

```bash
# 1. Create Virtual Cloud Network (VCN)
VCN_ID=$(oci network vcn create \
  --compartment-id $COMPARTMENT_ID \
  --cidr-block "10.0.0.0/16" \
  --display-name "vcn-vietcalendar" \
  --dns-label "vietcalendar" \
  --query 'data.id' --raw-output)

# 2. Create Internet Gateway
IGW_ID=$(oci network internet-gateway create \
  --compartment-id $COMPARTMENT_ID \
  --vcn-id $VCN_ID \
  --display-name "igw-vietcalendar" \
  --is-enabled true \
  --query 'data.id' --raw-output)

# 3. Add Default Route to Route Table
RT_ID=$(oci network vcn get --vcn-id $VCN_ID --query 'data."default-route-table-id"' --raw-output)
oci network route-table update \
  --rt-id $RT_ID \
  --route-rules '[{"destination":"0.0.0.0/0","destinationType":"CIDR_BLOCK","networkEntityId":"'$IGW_ID'"}]' \
  --force

# 4. Create Security List with Ingress Rules
SECLIST_ID=$(oci network security-list create \
  --compartment-id $COMPARTMENT_ID \
  --vcn-id $VCN_ID \
  --display-name "seclist-vietcalendar" \
  --egress-security-rules '[{"destination":"0.0.0.0/0","protocol":"all"}]' \
  --ingress-security-rules '[
    {"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"min":22,"max":22}},"description":"SSH"},
    {"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"min":80,"max":80}},"description":"HTTP 80"},
    {"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"min":443,"max":443}},"description":"HTTPS 443"},
    {"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"min":8080,"max":8080}},"description":"VietCalendar API 8080"},
    {"protocol":"17","source":"0.0.0.0/0","udpOptions":{"destinationPortRange":{"min":53,"max":53}},"description":"DNS UDP 53"},
    {"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"min":53,"max":53}},"description":"DNS TCP 53"},
    {"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"min":853,"max":853}},"description":"AdGuard DoT 853"},
    {"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"min":3000,"max":3000}},"description":"AdGuard Setup 3000"},
    {"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"min":8443,"max":8443}},"description":"AdGuard Web / DoH 8443"},
    {"protocol":"1","source":"0.0.0.0/0","icmpOptions":{"type":3,"code":4}}
  ]' \
  --query 'data.id' --raw-output)

# 5. Create Regional Public Subnet
SUBNET_ID=$(oci network subnet create \
  --compartment-id $COMPARTMENT_ID \
  --vcn-id $VCN_ID \
  --cidr-block "10.0.0.0/24" \
  --display-name "subnet-vcn-vietcalendar" \
  --dns-label "public" \
  --security-list-ids '["'$SECLIST_ID'"]' \
  --query 'data.id' --raw-output)
```

---

## 3. Allocate Always Free Reserved Static Public IP

```bash
PUBLIC_IP_ID=$(oci network public-ip create \
  --compartment-id $COMPARTMENT_ID \
  --lifetime "RESERVED" \
  --display-name "ip-vietcalendar-static" \
  --query 'data.id' --raw-output)

PUBLIC_IP_ADDR=$(oci network public-ip get --public-ip-id $PUBLIC_IP_ID --query 'data."ip-address"' --raw-output)
echo "Allocated Reserved Static IP: $PUBLIC_IP_ADDR"
```

---

## 4. Launch Compute Instance

### Launch AMD Shape (`VM.Standard.E2.1.Micro`):
```bash
INSTANCE_ID=$(oci compute instance launch \
  --compartment-id $COMPARTMENT_ID \
  --availability-domain "tTNg:AP-TOKYO-1-AD-1" \
  --shape "VM.Standard.E2.1.Micro" \
  --display-name "instance-oracle-linux-10" \
  --image-id "ocid1.image.oc1.ap-tokyo-1.aaaaaaaahgh5scxcd7whdaf3j6e73julskgpwts67ttbrn4mkr72x3bce5fa" \
  --subnet-id $SUBNET_ID \
  --assign-public-ip false \
  --ssh-authorized-keys-file ~/.ssh/id_ed25519.pub \
  --user-data-file cloud-init.sh.tpl \
  --query 'data.id' --raw-output)
```

### Or Launch Ampere A1 ARM Shape (`VM.Standard.A1.Flex` - 4 OCPUs / 24 GB RAM):
```bash
oci compute instance launch \
  --compartment-id $COMPARTMENT_ID \
  --availability-domain "tTNg:AP-TOKYO-1-AD-1" \
  --shape "VM.Standard.A1.Flex" \
  --shape-config '{"ocpus": 4, "memoryInGBs": 24}' \
  --display-name "instance-oracle-linux-10-arm" \
  --image-id "<ARM_IMAGE_OCID>" \
  --subnet-id $SUBNET_ID \
  --assign-public-ip false \
  --ssh-authorized-keys-file ~/.ssh/id_ed25519.pub \
  --user-data-file cloud-init.sh.tpl
```

---

## 5. Bind Reserved Static IP to Instance VNIC

```bash
# 1. Wait for instance to become RUNNING
oci compute instance get --instance-id $INSTANCE_ID --query 'data."lifecycle-state"'

# 2. Get Primary VNIC ID
VNIC_ID=$(oci compute vnic-attachment list \
  --instance-id $INSTANCE_ID \
  --compartment-id $COMPARTMENT_ID \
  --query 'data[0]."vnic-id"' --raw-output)

# 3. Get Primary Private IP ID
PRIVATE_IP_ID=$(oci network private-ip list \
  --vnic-id $VNIC_ID \
  --query 'data[0].id' --raw-output)

# 4. Associate the Reserved Static IP
oci network public-ip update \
  --public-ip-id $PUBLIC_IP_ID \
  --private-ip-id $PRIVATE_IP_ID \
  --force
```

---

## 6. Verification & Troubleshooting Commands

```bash
# 1. SSH into the instance
ssh -i ~/.ssh/id_ed25519 opc@$PUBLIC_IP_ADDR

# 2. Capture serial console output (for boot logs)
oci compute console-history capture --instance-id $INSTANCE_ID

# 3. Terminate instance without deleting static IP
oci compute instance terminate --instance-id $INSTANCE_ID --preserve-boot-volume false
```
