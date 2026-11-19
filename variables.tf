variable "tenancy_ocid" {
  description = "OCID of your OCI tenancy"
  type        = string
}

variable "compartment_ocid" {
  description = "OCID of the compartment where resources will be created (defaults to tenancy_ocid)"
  type        = string
  default     = ""
}

variable "region" {
  description = "OCI region (e.g. ap-tokyo-1, us-ashburn-1, etc.)"
  type        = string
  default     = "ap-tokyo-1"
}

variable "live_cluster_subnet_ocid" {
  description = "Existing live cluster subnet OCID to bind instances to (empty defaults to oci_core_subnet.public_subnet.id)"
  type        = string
  default     = ""
}

variable "ssh_allowed_cidrs" {
  description = "List of CIDR blocks permitted for SSH (port 22) ingress"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "ssh_public_key" {
  description = "Public SSH key for instance login"
  type        = string
}

variable "domain_name" {
  description = "Custom domain name (e.g. vinhthang.dev)"
  type        = string
  default     = "vinhthang.dev"
}
