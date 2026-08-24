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

variable "instance_shape" {
  description = "Always Free compute instance shape (VM.Standard.E2.1.Micro or VM.Standard.A1.Flex)"
  type        = string
  default     = "VM.Standard.E2.1.Micro"
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

variable "duckdns_domain" {
  description = "Legacy DuckDNS domain name fallback"
  type        = string
  default     = "thang-gcloud.duckdns.org"
}
