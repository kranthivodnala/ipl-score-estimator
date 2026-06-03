# ── variables.tf ───────────────────────────────────────────────────────────

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "ipl-score-predictor"
}

variable "cluster_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.30"
}

variable "node_instance_type" {
  description = "EC2 instance type for worker nodes"
  type        = string
  default     = "t3.medium"  # 2 vCPU, 4GB — enough for ML model serving
}

variable "node_desired_size" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 2
}

variable "node_min_size" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 3
}

variable "s3_bucket" {
  description = "S3 bucket for MLflow artifacts"
  type        = string
  default     = "ipl-score-estimator-mlflow-artifacts"
}

variable "mlflow_tracking_uri" {
  description = "MLflow tracking server URI"
  type        = string
  default     = "http://34.207.82.169:5000"
}

variable "dockerhub_image_a" {
  description = "DockerHub image for Model A"
  type        = string
  default     = "spidermanintegration/ipl-model-a:latest"
}

variable "dockerhub_image_b" {
  description = "DockerHub image for Model B"
  type        = string
  default     = "spidermanintegration/ipl-model-b:latest"
}
