# ── main.tf ────────────────────────────────────────────────────────────────
# IPL Score Predictor — EKS Cluster
# DevOps bridge: this is your Terraform modules from Disney/NBC
# but for Kubernetes instead of ECS

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }

  # Store state in S3 — same bucket you already have
  backend "s3" {
    bucket = "ipl-score-estimator-mlflow-artifacts"
    key    = "terraform/eks/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

# Kubernetes provider — connects to EKS after cluster is created
provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", var.cluster_name]
  }
}
