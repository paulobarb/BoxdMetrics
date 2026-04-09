variable "aws_region" {
  type        = string
  description = "AWS region to deploy resources"
  default     = "eu-north-1"
}

variable "project_name" {
  description = "The core name of the project"
  type        = string
  default     = "boxdmetrics"
}

variable "environment" {
  type        = string
  description = "The deployment environment (e.g., dev, staging, prod)"
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "container_port" {
  description = "The port the Docker container listens on"
  type        = number
  default     = 8000
}

variable "task_cpu" {
  description = "Fargate instance CPU units to provision (1 vCPU = 1024)"
  type        = number
  default     = 256
}

variable "task_memory" {
  description = "Fargate instance memory to provision (in MiB)"
  type        = number
  default     = 512
}

variable "api_secret_key" {
  description = "Secret password for the FastAPI backend"
  type        = string
  sensitive   = true
}

variable "duckdns_token" {
  description = "Secret token for DuckDNS dynamic IP updates"
  type = string
  sensitive = true
}