# AEGIS Helm Chart

Deploy the AEGIS Healthcare Intelligence Platform on Kubernetes.

## Prerequisites

- Kubernetes 1.25+
- Helm 3.10+
- kubectl configured for your cluster
- (Optional) AWS credentials for Bedrock LLM

## Quick Start

```bash
# Add required Helm repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add opensearch https://opensearch-project.github.io/helm-charts
helm repo update

# Create namespace
kubectl create namespace aegis

# Create secrets (replace with your values)
kubectl create secret generic aegis-secrets \
  --namespace aegis \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --from-literal=jwt-secret=$(openssl rand -hex 32) \
  --from-literal=postgres-password=$(openssl rand -hex 16) \
  --from-literal=redis-password=$(openssl rand -hex 16)

# Install the chart
helm install aegis ./deploy/helm/aegis \
  --namespace aegis \
  --values ./deploy/helm/aegis/values.yaml

# Check deployment status
kubectl get pods -n aegis
```

## Configuration

### Minimal Production Setup

```yaml
# values-production.yaml
api:
  replicaCount: 3
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi

postgresql:
  primary:
    persistence:
      size: 100Gi

redis:
  master:
    persistence:
      size: 20Gi

opensearch:
  replicas: 3
  persistence:
    size: 100Gi
```

### AWS Integration

```yaml
# values-aws.yaml
aws:
  region: us-east-1
  
  neptune:
    enabled: true
    endpoint: "your-neptune-cluster.cluster-xxx.us-east-1.neptune.amazonaws.com"
  
  bedrock:
    enabled: true
    modelId: "anthropic.claude-3-sonnet-20240229-v1:0"
  
  cognito:
    enabled: true
    userPoolId: "us-east-1_xxx"
    clientId: "xxx"

serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::123456789:role/aegis-eks-role"
```

### Installing with Custom Values

```bash
helm install aegis ./deploy/helm/aegis \
  --namespace aegis \
  --values ./deploy/helm/aegis/values-production.yaml \
  --values ./deploy/helm/aegis/values-aws.yaml
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │ Ingress │→ │ API Pod │  │ API Pod │  (HPA: 2-10 pods)   │
│  └────┬────┘  └────┬────┘  └────┬────┘                     │
│       │            │            │                           │
│  ┌────┴────────────┴────────────┴────┐                     │
│  │          Services Layer           │                     │
│  └────┬────────┬────────┬────────┬───┘                     │
│       │        │        │        │                          │
│  ┌────┴──┐ ┌───┴───┐ ┌──┴──┐ ┌──┴───┐                      │
│  │Postgres│ │ Redis │ │Open │ │Kafka │                      │
│  │  (PG)  │ │       │ │Search│ │      │                     │
│  └────────┘ └───────┘ └─────┘ └──────┘                      │
│                                                              │
│  External: AWS Neptune, Bedrock, Cognito                     │
└─────────────────────────────────────────────────────────────┘
```

## Monitoring

The chart includes Prometheus ServiceMonitor for metrics collection.

```bash
# Port-forward Grafana
kubectl port-forward svc/aegis-grafana 3000:80 -n aegis

# Access at http://localhost:3000
```

## Troubleshooting

### Check pod logs
```bash
kubectl logs -f deployment/aegis-api -n aegis
```

### Check health endpoints
```bash
kubectl port-forward svc/aegis-api 8000:8000 -n aegis
curl http://localhost:8000/health
```

### Database connectivity
```bash
kubectl exec -it aegis-postgresql-0 -n aegis -- psql -U aegis -d aegis
```

## Upgrades

```bash
helm upgrade aegis ./deploy/helm/aegis \
  --namespace aegis \
  --values ./deploy/helm/aegis/values.yaml
```

## Uninstall

```bash
helm uninstall aegis --namespace aegis
kubectl delete namespace aegis
```

## Security

- All secrets should be managed via AWS Secrets Manager or HashiCorp Vault
- Network policies restrict pod-to-pod communication
- Pod security context enforces non-root execution
- TLS is required for all external traffic
