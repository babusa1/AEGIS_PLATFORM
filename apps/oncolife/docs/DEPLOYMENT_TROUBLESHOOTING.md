# OncoLife Deployment Troubleshooting Guide

**Quick fixes for common deployment issues**

---

## 🚨 Most Common Issues (Check These First!)

### Issue #1: Windows Path Mangling (Git Bash)

**Symptom:**
```
InvalidParameterException: Invalid parameter: /ecs/oncolife-patient-api
```
or
```
Parameter format not valid: C:/Program Files/Git/ecs/...
```

**Cause:** Git Bash on Windows converts forward slashes to Windows paths.

**Fix:** Use **PowerShell** instead of Git Bash for ALL AWS CLI commands.

```powershell
# ✅ Correct (PowerShell):
aws logs create-log-group --log-group-name "/ecs/oncolife-patient-api"

# ❌ Wrong (Git Bash) - will mangle the path
```

---

### Issue #2: ECS Service-Linked Role Missing

**Symptom:**
```
InvalidParameterException: Unable to assume role...
```
or cluster creation fails.

**Cause:** ECS service-linked role doesn't exist.

**Fix:** Create it FIRST (before any ECS operations):

```powershell
aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com
# If you get "already exists" error - that's OK, continue
```

---

### Issue #3: Subnets in Wrong Format

**Symptom:**
```
InvalidParameterException: subnets is not valid
```

**Cause:** Subnet IDs passed incorrectly (quotes issue).

**Fix:** Use this format in PowerShell:

```powershell
# ✅ Correct:
--network-configuration "awsvpcConfiguration={subnets=[subnet-abc123,subnet-def456],securityGroups=[sg-123456],assignPublicIp=DISABLED}"

# ❌ Wrong (extra quotes):
--network-configuration "awsvpcConfiguration={subnets=['subnet-abc123','subnet-def456']..."
```

---

### Issue #4: Secrets Manager ARN Format Wrong

**Symptom:**
```
ResourceNotFoundException: Secrets Manager can't find the specified secret
```
or
```
AccessDeniedException: User is not authorized to access this resource
```

**Cause:** Task definition has wrong secret ARN format.

**Fix:** Get the FULL secret ARN including the random suffix:

```powershell
# Get the full ARN (note the -XXXXXX suffix)
aws secretsmanager describe-secret --secret-id "oncolife/db" --query 'ARN' --output text

# Result looks like:
# arn:aws:secretsmanager:us-west-2:123456789:secret:oncolife/db-AbCdEf

# Use the FULL ARN in your task definition, including the suffix!
```

---

### Issue #5: Docker Build Context Wrong

**Symptom:**
```
COPY failed: file not found in build context
```
or
```
failed to compute cache key: "/requirements.txt" not found
```

**Cause:** Building from wrong directory.

**Fix:** Build from the correct directory:

```powershell
# Make sure you're in the monolith root
cd Oncolife_Monolith

# Patient API - build from root, specify Dockerfile path
docker build -t oncolife-patient-api:latest -f apps/patient-platform/patient-api/Dockerfile apps/patient-platform/patient-api/

# OR cd into the app directory first
cd apps/patient-platform/patient-api
docker build -t oncolife-patient-api:latest .
```

---

### Issue #6: ECR Login Expired

**Symptom:**
```
denied: Your authorization token has expired. Reauthenticate and try again.
```
or
```
no basic auth credentials
```

**Cause:** ECR login token expires after 12 hours.

**Fix:** Re-login to ECR:

```powershell
$ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com"
```

---

### Issue #7: RDS Not Accessible from ECS

**Symptom:**
- Tasks start but immediately fail
- Health checks timeout
- Logs show: `Connection refused` or `timeout` to database

**Cause:** Security group rules don't allow traffic.

**Fix:** Verify security group allows PostgreSQL from ECS:

```powershell
# Check RDS security group allows inbound from ECS security group
aws ec2 describe-security-groups --group-ids sg-YOUR_RDS_SG --query 'SecurityGroups[0].IpPermissions'

# Should show port 5432 with source = ECS security group
# If not, add the rule:
aws ec2 authorize-security-group-ingress `
    --group-id sg-YOUR_RDS_SG `
    --protocol tcp `
    --port 5432 `
    --source-group sg-YOUR_ECS_SG
```

---

### Issue #8: Task Stuck in PENDING Forever

**Symptom:**
- `aws ecs describe-services` shows `desiredCount: 2, runningCount: 0`
- Tasks stay in PENDING state

**Causes & Fixes:**

**A) No NAT Gateway** - Private subnets can't reach ECR:
```
Solution: Ensure private subnets have route to NAT Gateway
```

**B) Wrong subnets** - Using public instead of private:
```powershell
# ECS tasks should use PRIVATE subnets
# ALB should use PUBLIC subnets
```

**C) Task execution role missing permissions**:
```powershell
# Ensure role has ECR and Secrets Manager access
aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
```

---

### Issue #9: ALB Returns 502 Bad Gateway

**Symptom:**
- ALB health check fails
- Browser shows "502 Bad Gateway"

**Causes & Fixes:**

**A) Wrong container port in target group**:
```
Patient API should be port 8000
Doctor API should be port 8001
```

**B) Health check path wrong**:
```
Should be: /health (not /api/v1/health or /)
```

**C) Container not healthy yet** - increase grace period:
```powershell
aws ecs update-service `
    --cluster oncolife-production `
    --service patient-api-service `
    --health-check-grace-period-seconds 180
```

---

### Issue #10: "InvalidParameterValue" on create-db-instance

**Symptom:**
```
InvalidParameterValue: The parameter MasterUserPassword is not a valid password
```

**Cause:** Password doesn't meet requirements.

**Fix:** Use a valid password:
```
Requirements:
- At least 8 characters
- Cannot contain: /, @, ", or spaces
- Must have letters and numbers

Good: MySecure2026Pass!
Bad: My@Pass/123
```

---

## 🔧 Quick Diagnostic Commands

### Check Your AWS Setup
```powershell
# Verify AWS credentials work
aws sts get-caller-identity

# Check your region
aws configure get region

# List your VPCs
aws ec2 describe-vpcs --query 'Vpcs[*].[VpcId,Tags[?Key==`Name`].Value|[0]]' --output table
```

### Check ECS Status
```powershell
# List services and their status
aws ecs describe-services `
    --cluster oncolife-production `
    --services patient-api-service doctor-api-service `
    --query 'services[*].{Name:serviceName,Status:status,Desired:desiredCount,Running:runningCount,Pending:pendingCount}' `
    --output table

# Get recent task failures
aws ecs list-tasks --cluster oncolife-production --desired-status STOPPED --query 'taskArns[0:3]'

# Describe a failed task (use ARN from above)
aws ecs describe-tasks --cluster oncolife-production --tasks TASK_ARN --query 'tasks[0].{status:lastStatus,reason:stoppedReason}'
```

### Check Logs
```powershell
# View recent Patient API logs
aws logs tail "/ecs/oncolife-patient-api" --since 30m

# View with errors highlighted
aws logs filter-log-events `
    --log-group-name "/ecs/oncolife-patient-api" `
    --filter-pattern "ERROR" `
    --start-time (Get-Date).AddMinutes(-30).ToUniversalTime().Subtract((Get-Date "1/1/1970")).TotalMilliseconds
```

### Check Target Group Health
```powershell
# Get target group ARN
$TG_ARN = (aws elbv2 describe-target-groups --names "patient-api-tg" --query 'TargetGroups[0].TargetGroupArn' --output text)

# Check health
aws elbv2 describe-target-health --target-group-arn $TG_ARN
```

### Check RDS Status
```powershell
aws rds describe-db-instances `
    --db-instance-identifier oncolife-db `
    --query 'DBInstances[0].{Status:DBInstanceStatus,Endpoint:Endpoint.Address,Port:Endpoint.Port}'
```

---

## 📋 Pre-Deployment Checklist

Run through this before starting deployment:

```
□ AWS CLI installed and configured (aws sts get-caller-identity works)
□ Docker Desktop installed and running
□ Using PowerShell (not Git Bash) for AWS commands
□ Region set correctly (us-west-2 or your region)
□ Have Administrator access to AWS account
□ Noted down all IDs as you create resources
```

---

## 🆘 Still Stuck?

If you're still having issues, collect this information:

1. **Which phase/step are you on?**
2. **Exact command you ran**
3. **Complete error message** (screenshot or copy/paste)
4. **Your environment** (Windows/Mac/Linux, PowerShell/Bash)
5. **Output of:** `aws sts get-caller-identity`

---

## 📞 Common Error → Solution Quick Reference

| Error Contains | Solution |
|----------------|----------|
| `Invalid parameter: /ecs/...` | Use PowerShell, not Git Bash |
| `Unable to assume role` | Create ECS service-linked role first |
| `authorization token has expired` | Re-login to ECR |
| `Connection refused` to database | Check security group rules |
| `PENDING` tasks forever | Check NAT Gateway and subnets |
| `502 Bad Gateway` | Check container port and health path |
| `secret not found` | Use full ARN with -XXXXXX suffix |
| `COPY failed` in Docker | Check build context directory |

---

*Last Updated: January 2026*
