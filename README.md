# IPL Score Predictor — A/B Test on EKS
**Project 4 of Kranthi's MLOps 20-Hour Plan**

A production-grade MLOps system that predicts IPL T20 first innings scores using two competing ML models deployed on Amazon EKS with an 80/20 A/B traffic split — the same canary deployment pattern used in enterprise software releases, applied to machine learning.

---

## The Problem

Which ML model predicts IPL scores better — a baseline XGBoost model trained on venue and team history, or a LightGBM challenger that also accounts for dew factor, recent form, head-to-head averages, and home ground advantage? This project answers that question using a live A/B test running on Kubernetes.

---

## Architecture

```
User Request
    → AWS ALB (80/20 weighted routing)
        → 80% → ipl-model-a (XGBoost v1.0)  → EKS Pod
        → 20% → ipl-model-b (LightGBM v2.0) → EKS Pod
                                ↓
                    MLflow on EC2 (model registry)
                                ↓
                    S3 (model artifacts)
                                ↓
                    AWS Secrets Manager (credentials)
```

---

## Stack

| Layer | Technology |
|---|---|
| Data | IPL ball-by-ball dataset (283k deliveries, 2008–2026) |
| ML | XGBoost, LightGBM, scikit-learn |
| Experiment Tracking | MLflow on EC2 with S3 artifact store |
| Containerization | Docker, DockerHub |
| Orchestration | Amazon EKS (Kubernetes 1.30) |
| Infrastructure | Terraform (VPC, EKS, IAM, IRSA) |
| Secrets | AWS Secrets Manager + Secrets Store CSI Driver |
| Load Balancing | AWS ALB via Load Balancer Controller |
| API | FastAPI |
| Frontend | HTML/CSS/JS served via nginx |

---

## Models

| | Model A | Model B |
|---|---|---|
| Algorithm | XGBoost v1.0 | LightGBM v2.0 |
| Stage | Production | Staging |
| Features | 9 | 16 |
| Traffic | 80% | 20% |
| Extra features | — | Dew factor, recent form, H2H avg, home ground, modern era |
| MAE | 32.9 runs | 31.3 runs |

### Features engineered
- Venue average score (Wankhede vs Chepauk play very differently)
- Batting team all-time average and rolling 10-match average
- Toss decision flag
- Season year and month (scores rising each year post-2020)
- Head-to-head average between the two teams
- Dew factor (evening matches at dew-prone venues)
- Recent form ratio (last 5 vs last 10 match average)
- Bowling team average conceded
- Home ground advantage flag

---

## Project Structure

```
ipl-score-predictor/
├── app/
│   └── main.py                  # FastAPI app — loads models from MLflow
├── frontend/
│   └── index.html               # Cricket-themed A/B test UI
├── terraform/
│   ├── main.tf                  # Provider + S3 backend
│   ├── variables.tf             # Cluster config
│   ├── vpc.tf                   # VPC, subnets, NAT gateway
│   ├── eks.tf                   # EKS cluster + node group + IAM
│   ├── irsa.tf                  # IRSA for pod-level AWS permissions
│   ├── outputs.tf               # Cluster endpoint, kubeconfig command
│   └── kubernetes/
│       ├── namespace.yml
│       ├── service-account.yml  # Links to IAM role via IRSA
│       ├── secrets-store.yml    # Pulls from AWS Secrets Manager
│       ├── model-a-deployment.yml
│       ├── model-b-deployment.yml
│       ├── services.yml
│       └── ingress.yml          # ALB with 80/20 weighted routing
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── requirements.txt
└── ipl_score_predictor_step1.ipynb  # Training notebook
```

---

## Setup

### Prerequisites
- AWS CLI configured (`aws configure`)
- Terraform >= 1.0
- kubectl
- Helm
- Docker

### 1. Train the models

```bash
# Start MLflow with S3 artifact store
mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root s3://your-bucket/mlflow \
  --host 0.0.0.0 \
  --port 5000

# Run the training notebook
jupyter notebook ipl_score_predictor_step1.ipynb
```

### 2. Create secrets in AWS Secrets Manager

```bash
aws secretsmanager create-secret \
  --name "ipl-score-predictor/app-secrets" \
  --region us-east-1 \
  --secret-string '{
    "AWS_ACCESS_KEY_ID": "your_key",
    "AWS_SECRET_ACCESS_KEY": "your_secret",
    "AWS_DEFAULT_REGION": "us-east-1",
    "MLFLOW_TRACKING_URI": "http://your-mlflow-ec2:5000"
  }'
```

### 3. Build and push Docker images

```bash
docker-compose build
docker tag ipl-score-estimator-model-a your-dockerhub/ipl-model-a:latest
docker tag ipl-score-estimator-model-b your-dockerhub/ipl-model-b:latest
docker push your-dockerhub/ipl-model-a:latest
docker push your-dockerhub/ipl-model-b:latest
```

### 4. Deploy EKS cluster with Terraform

```bash
cd terraform
terraform init
terraform apply
```

### 5. Configure kubectl

```bash
aws eks update-kubeconfig --region us-east-1 --name ipl-score-predictor
```

### 6. Install add-ons

```bash
# AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=ipl-score-predictor \
  --set region=us-east-1 \
  --set vpcId=your-vpc-id

# Secrets Store CSI Driver
helm repo add secrets-store-csi-driver \
  https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm install csi-secrets-store \
  secrets-store-csi-driver/secrets-store-csi-driver \
  --namespace kube-system \
  --set syncSecret.enabled=true

# AWS Secrets Manager Provider
kubectl apply -f https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml
```

### 7. Deploy application

```bash
kubectl apply -f kubernetes/namespace.yml
kubectl apply -f kubernetes/service-account.yml
kubectl apply -f kubernetes/secrets-store.yml
kubectl apply -f kubernetes/model-a-deployment.yml
kubectl apply -f kubernetes/model-b-deployment.yml
kubectl apply -f kubernetes/services.yml
kubectl apply -f kubernetes/ingress.yml
```

### 8. Get the ALB endpoint

```bash
kubectl get ingress -n ipl-score-predictor
```

---

## Test the API

```bash
# Health check
curl http://<alb-hostname>/health

# Predict MI vs CSK at Wankhede
curl -X POST http://<alb-hostname>/predict \
  -H "Content-Type: application/json" \
  -d '{
    "batting_team": "Mumbai Indians",
    "bowling_team": "Chennai Super Kings",
    "venue": "Wankhede Stadium",
    "toss_winner": "batting",
    "month": 4,
    "year": 2025
  }'
```

Expected response:
```json
{
  "match": "Mumbai Indians vs Chennai Super Kings",
  "venue": "Wankhede Stadium",
  "stage": "Production",
  "algorithm": "XGBoost v1.0",
  "features": 9,
  "prediction": 167,
  "latency_ms": 5.4
}
```

---

## Local Development

```bash
# Start containers locally
docker-compose up

# Frontend
open http://localhost:3000

# Model A API
curl http://localhost:8001/health

# Model B API
curl http://localhost:8002/health
```

---

## Cost Control

```bash
# Destroy EKS when not testing (~$6/day while running)
cd terraform
terraform destroy

# Stop MLflow EC2 when not needed
aws ec2 stop-instances --instance-ids your-instance-id
```

---

## Key MLOps Learnings

- S3 as MLflow artifact store makes models portable across local, Docker, and EKS — no file paths or volume mounts needed
- IRSA eliminates hardcoded AWS credentials in pods — the Kubernetes equivalent of ECS Task Roles
- AWS Secrets Manager + CSI Driver syncs secrets into pods at runtime — nothing sensitive in YAML or Docker images
- The A/B test pattern (80/20 ALB split) is identical to canary deployments in software — same infrastructure, ML payload
- MLflow aliases (`@Production`, `@Staging`) replace deprecated stage transitions in MLflow 3.x

---

## DevOps → MLOps Bridge

| ECS services | Kubernetes Deployments |
| ECS Task Role | IRSA (IAM Role for Service Account) |
| ALB weighted target groups | Kubernetes Ingress with ALB annotations |
| Docker + ECR | Docker + DockerHub |
| Terraform modules | Same — EKS instead of ECS |
| Jenkins pipelines | MLflow experiment tracking |
| Artifactory | MLflow Model Registry |
| CloudWatch | Kubernetes logs + ALB metrics |
| AWS Secrets Manager | Same — accessed via CSI Driver |