variable "namespace" {
  type        = string
  description = "Kubernetes namespace for the Ingress (e.g., dev)."
}

variable "domain" {
  type        = string
  description = "Apex domain. studio.<domain> is the ingress host."
}

variable "acme_email" {
  type        = string
  description = "Let's Encrypt registration email."
}

variable "studio_service_name" {
  type        = string
  default     = "supabase-studio"
  description = "K8s Service name backing the Studio Ingress."
}

variable "studio_service_port" {
  type        = number
  default     = 3000
  description = "K8s Service port for Studio."
}

variable "api_service_name" {
  type        = string
  default     = "api"
  description = "K8s Service name for the FastAPI backend (must exist in var.namespace)."
}

variable "api_service_port" {
  type        = number
  default     = 80
  description = "K8s Service port for the API (Service exposes 80→8000 on the pod)."
}

variable "frontend_service_name" {
  type        = string
  default     = "frontend"
  description = "K8s Service name for the Angular frontend."
}

variable "frontend_service_port" {
  type        = number
  default     = 80
  description = "K8s Service port for the frontend."
}

variable "staging_namespace" {
  type        = string
  default     = "staging"
  description = "Kubernetes namespace for the staging Ingress (separate from var.namespace=dev)."
}
