variable "project_id" {
  description = "GCP project ID hosting the gce10 Always Free instance"
  type        = string
}

variable "region" {
  description = "GCP region for Always Free resources"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone for the gce10 e2-micro instance"
  type        = string
  default     = "us-central1-a"
}

variable "static_ip_address" {
  description = "Reserved static external IPv4 address for gce10"
  type        = string
  default     = "35.209.149.46"
}

variable "ssh_public_key" {
  description = "SSH public key authorized for instance login"
  type        = string
}
