# ── irsa.tf ────────────────────────────────────────────────────────────────
# IRSA = IAM Roles for Service Accounts
# DevOps bridge: same as ECS Task Role but for Kubernetes pods
# Pods get AWS permissions via IAM role — no credentials needed in YAML

# ── OIDC Provider for EKS ─────────────────────────────────────────────────
data "aws_eks_cluster" "main" {
  name = aws_eks_cluster.main.name
}

data "tls_certificate" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

# ── IAM Role for pods (IRSA) ──────────────────────────────────────────────
data "aws_iam_policy_document" "irsa_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.eks.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:sub"
      values   = ["system:serviceaccount:ipl-score-predictor:ipl-service-account"]
    }
  }
}

resource "aws_iam_role" "irsa" {
  name               = "${var.cluster_name}-irsa-role"
  assume_role_policy = data.aws_iam_policy_document.irsa_assume_role.json
}

# ── IAM Policy — S3 + Secrets Manager access ─────────────────────────────
resource "aws_iam_role_policy" "irsa_policy" {
  name = "${var.cluster_name}-irsa-policy"
  role = aws_iam_role.irsa.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # S3 — pull MLflow artifacts
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket", "s3:PutObject"]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket}",
          "arn:aws:s3:::${var.s3_bucket}/*"
        ]
      },
      {
        # Secrets Manager — read app secrets
        Effect   = "Allow"
        Action   = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          "arn:aws:secretsmanager:us-east-1:893918474791:secret:ipl-score-predictor/app-secrets-pvCGZY"
        ]
      }
    ]
  })
}

# ── Output the role ARN (used in Kubernetes service account) ───────────────
output "irsa_role_arn" {
  description = "IAM role ARN for pod service account"
  value       = aws_iam_role.irsa.arn
}
