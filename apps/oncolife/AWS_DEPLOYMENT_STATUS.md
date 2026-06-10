# AWS Deployment Status - COMPLETE ✅

**Last Updated:** January 21, 2026
**Region:** us-east-1
**Account:** 296062592436
**Environment:** Staging/Development

---

## 🎉 DEPLOYMENT COMPLETE!

### Frontend URLs 
| App | HTTPS (CloudFront) | HTTP (S3) |
|-----|---------------------|-----------|
| **Patient Portal** | https://d1np153spw37t4.cloudfront.net | http://oncolife-patient-web-296062592436.s3-website-us-east-1.amazonaws.com |
| **Doctor Portal** | https://d14xcx5hwgubw5.cloudfront.net | http://oncolife-doctor-web-296062592436.s3-website-us-east-1.amazonaws.com |

### Backend APIs (HTTPS via CloudFront → ALB)
| API | HTTPS URL | Swagger Docs |
|-----|-----------|--------------|
| **Patient API** | https://doreebziauwxa.cloudfront.net | [/docs](https://doreebziauwxa.cloudfront.net/docs) |
| **Doctor API** | https://d3laeu67onw47.cloudfront.net | [/docs](https://d3laeu67onw47.cloudfront.net/docs) |

---

## ✅ All Components Deployed

### Networking
| Resource | ID |
|----------|-----|
| VPC | `vpc-036fb39078fab6ab0` |
| Public Subnet 1 | `subnet-0c14abcaa4b8b34b3` |
| Public Subnet 2 | `subnet-04d9f4ab389bc26e1` |
| Private Subnet 1 | `subnet-0521ca12386ca3f36` |
| Private Subnet 2 | `subnet-08fac9d264f6c64a8` |
| Internet Gateway | `igw-0b90ccb09b8109c07` |
| NAT Gateway | `nat-04903058172b44f40` |

### Security Groups
| Resource | ID |
|----------|-----|
| ALB Security Group | `sg-033433ed2872e6dde` |
| ECS Security Group | `sg-02e1b6580c48f07b6` |
| RDS Security Group | `sg-0fdb8682fd33797e8` |
| Bastion Security Group | `sg-080936ec7b90c969c` |

### Database (RDS PostgreSQL)
| Resource | Value |
|----------|-------|
| RDS Instance | `oncolife-db` |
| RDS Endpoint | `oncolife-db.cziyoqoiu475.us-east-1.rds.amazonaws.com` |
| DB Username | `oncolife_admin` |
| DB Password | `<REDACTED_ROTATE_ME>` |
| Port | `5432` |
| Databases | `oncolife_patient`, `oncolife_doctor` |

### Authentication (Cognito)
| Resource | Value |
|----------|-------|
| User Pool ID | `us-east-1_cRcMOPVCB` |
| Client ID | `3ti7okjro11ppdld13v0bo2fpi` |
| Client Secret | `<REDACTED_ROTATE_ME>` |

### Load Balancers
| Resource | DNS |
|----------|-----|
| Patient ALB | `oncolife-patient-alb-1736472057.us-east-1.elb.amazonaws.com` |
| Doctor ALB | `oncolife-doctor-alb-2035093014.us-east-1.elb.amazonaws.com` |

### S3 Buckets (Active - us-east-1)
| Bucket | Purpose | Region |
|--------|---------|--------|
| `oncolife-patient-web-296062592436` | Patient Portal static files | us-east-1 ✅ |
| `oncolife-doctor-web-296062592436` | Doctor Portal static files | us-east-1 ✅ |
| `oncolife-education-east-296062592436` | Education PDFs (85+ files) | us-east-1 ✅ |

### S3 Buckets (Legacy - us-west-2) ⚠️ NOT DELETED
| Bucket | Purpose | Region | Status |
|--------|---------|--------|--------|
| `oncolife-education-296062592436` | OLD Education PDFs | us-west-2 | ⚠️ Kept (30.8 MiB) |
| `oncolife-referrals-296062592436` | Fax/referral documents | us-west-2 | ⚠️ Kept (236 KiB) |

> **Note:** Legacy buckets in us-west-2 were NOT deleted (minimal cost ~$0.01/month). 
> They can be deleted later if not needed. The application now uses us-east-1 buckets.

### Container Registry (ECR)
| Repository | Status |
|------------|--------|
| `oncolife-patient-api` | ✅ Image pushed |
| `oncolife-doctor-api` | ✅ Image pushed |

### EC2 Bastion Server (For RDS Access)
| Resource | Value | Status |
|----------|-------|--------|
| Instance ID | `i-020ffd06310dab4bc` | 🔴 **STOPPED** |
| Type | t2.micro | - |
| Name | `oncolife-bastion` | - |
| Security Group | `sg-080936ec7b90c969c` | - |

> **Note:** Bastion is stopped to save costs (~$8/month). Start it when you need direct RDS access.
> 
> **To restart:**
> ```bash
> aws ec2 start-instances --instance-ids i-020ffd06310dab4bc --region us-east-1
> aws ec2 describe-instances --instance-ids i-020ffd06310dab4bc --query "Reservations[*].Instances[*].PublicIpAddress" --output text --region us-east-1
> ```

### ECS
| Resource | Status |
|----------|--------|
| Cluster | `oncolife-production` ✅ |
| Patient API Service | ✅ Running |
| Doctor API Service | ✅ Running |

### CloudFront Distributions
| App | CloudFront ID | Domain |
|-----|---------------|--------|
| Patient Portal | `E33AUPKTFUG96P` | https://d1np153spw37t4.cloudfront.net |
| Doctor Portal | `E2GRY718GCD95L` | https://d14xcx5hwgubw5.cloudfront.net |
| Patient API | `EBVJGZLVU43TZ` | https://doreebziauwxa.cloudfront.net |
| Doctor API | `E1LRE6KACN1FG3` | https://d3laeu67onw47.cloudfront.net |

---

## 🔑 ALL CREDENTIALS

```
AWS Account:        296062592436
AWS Region:         us-east-1

# Database
RDS Endpoint:       oncolife-db.cziyoqoiu475.us-east-1.rds.amazonaws.com
RDS Username:       oncolife_admin
RDS Password:       <REDACTED_ROTATE_ME>
RDS Port:           5432

# Cognito
Cognito Pool ID:    us-east-1_cRcMOPVCB
Cognito Client ID:  3ti7okjro11ppdld13v0bo2fpi
Cognito Secret:     <REDACTED_ROTATE_ME>

# Frontend URLs (HTTPS via CloudFront)
Patient Portal:     https://d1np153spw37t4.cloudfront.net
Doctor Portal:      https://d14xcx5hwgubw5.cloudfront.net

# Backend APIs (HTTPS via CloudFront)
Patient API:        https://doreebziauwxa.cloudfront.net
Doctor API:         https://d3laeu67onw47.cloudfront.net

# Direct ALB (HTTP only, internal)
Patient ALB:        http://oncolife-patient-alb-1736472057.us-east-1.elb.amazonaws.com
Doctor ALB:         http://oncolife-doctor-alb-2035093014.us-east-1.elb.amazonaws.com

# S3 Buckets (Active - us-east-1)
Patient Web:        oncolife-patient-web-296062592436
Doctor Web:         oncolife-doctor-web-296062592436
Education:          oncolife-education-east-296062592436

# S3 Buckets (Legacy - us-west-2, NOT DELETED)
Referrals (OLD):    oncolife-referrals-296062592436
Education (OLD):    oncolife-education-296062592436
```

---

## 🔐 GitHub Secrets for CI/CD

Configure these secrets in your GitHub repository (Settings → Secrets → Actions):

| Secret Name | Value |
|-------------|-------|
| `AWS_ACCOUNT_ID` | `296062592436` |
| `AWS_ACCESS_KEY_ID` | (your IAM access key) |
| `AWS_SECRET_ACCESS_KEY` | (your IAM secret key) |
| `PATIENT_DATABASE_URL` | `postgresql://oncolife_admin:<REDACTED_ROTATE_ME>@oncolife-db.cziyoqoiu475.us-east-1.rds.amazonaws.com:5432/oncolife_patient` |
| `DOCTOR_DATABASE_URL` | `postgresql://oncolife_admin:<REDACTED_ROTATE_ME>@oncolife-db.cziyoqoiu475.us-east-1.rds.amazonaws.com:5432/oncolife_doctor` |
| `PATIENT_API_URL` | `https://doreebziauwxa.cloudfront.net/api/v1` |
| `DOCTOR_API_URL` | `https://d3laeu67onw47.cloudfront.net/api/v1` |
| `PATIENT_WS_URL` | `wss://doreebziauwxa.cloudfront.net/api/v1` |
| `PATIENT_WEB_BUCKET` | `oncolife-patient-web-296062592436` |
| `DOCTOR_WEB_BUCKET` | `oncolife-doctor-web-296062592436` |
| `PATIENT_CLOUDFRONT_ID` | `E33AUPKTFUG96P` |
| `DOCTOR_CLOUDFRONT_ID` | `E2GRY718GCD95L` |

---

## 🧪 Test Accounts

### Test Patient
- UUID: `11111111-1111-1111-1111-111111111111`
- Email: `test@oncolife.local`
- Name: Test Patient

### Test Doctor
- UUID: `22222222-2222-2222-2222-222222222222`
- Email: `doctor@oncolife.local`
- Name: Test Doctor
- Role: Physician
- NPI: 1234567890

---

## 💰 Estimated Monthly Cost

| Service | Cost/Month | Notes |
|---------|------------|-------|
| RDS db.t3.medium | ~$37 | Database |
| NAT Gateway | ~$32 | Network |
| ECS Fargate (2 services) | ~$29 | Backend APIs |
| ALBs (2) | ~$36 | Load Balancers |
| S3 + CloudWatch | ~$5 | Storage + Logs |
| CloudFront | ~$5 | CDN/HTTPS |
| Bastion EBS (stopped) | ~$0.50 | Stopped instance storage |
| **Total** | **~$145/month** | |

> **Cost Optimization Applied:**
> - ✅ Bastion server STOPPED (saves ~$8/month)
> - ⚠️ Legacy S3 buckets in us-west-2 kept (minimal cost ~$0.01/month)

---

## ✅ Deployment Checklist

- [x] VPC and Networking ✅
- [x] RDS PostgreSQL Database ✅
- [x] ECS Cluster and Services ✅
- [x] Application Load Balancers ✅
- [x] S3 Buckets for Frontends ✅
- [x] CloudFront for HTTPS ✅
- [x] Patient Portal Deployed ✅
- [x] Doctor Portal Deployed ✅
- [x] Patient API Deployed ✅
- [x] Doctor API Deployed ✅
- [x] Education PDFs to S3 ✅
- [x] Demo Mode Working ✅
- [x] Bastion Server Stopped (cost savings) ✅
- [ ] Configure GitHub Secrets for CI/CD
- [ ] Custom Domain (optional)
- [ ] CloudWatch Alarms (optional)
- [ ] Delete legacy S3 buckets in us-west-2 (optional)

---

## 🧹 Cleanup Commands (Optional)

### Start Bastion Server (when needed for RDS access)
```bash
aws ec2 start-instances --instance-ids i-020ffd06310dab4bc --region us-east-1
# Wait ~30 seconds, then get the new public IP:
aws ec2 describe-instances --instance-ids i-020ffd06310dab4bc --query "Reservations[*].Instances[*].[State.Name,PublicIpAddress]" --output table --region us-east-1
```

### Stop Bastion Server (to save costs)
```bash
aws ec2 stop-instances --instance-ids i-020ffd06310dab4bc --region us-east-1
```

### Delete Legacy S3 Buckets (optional - if not needed)
```bash
# Delete old education bucket in us-west-2
aws s3 rb s3://oncolife-education-296062592436 --force --region us-west-2

# Delete old referrals bucket in us-west-2
aws s3 rb s3://oncolife-referrals-296062592436 --force --region us-west-2
```

---

*Last Updated: January 22, 2026*
