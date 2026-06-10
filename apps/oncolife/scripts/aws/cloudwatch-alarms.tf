# =============================================================================
# CloudWatch Alarms for OncoLife Production Monitoring
# =============================================================================
# 
# This Terraform configuration creates CloudWatch Alarms for:
# - ECS service health (CPU, Memory, Task count)
# - Application Load Balancer health (5xx errors, latency)
# - RDS database health (connections, CPU, storage)
# - Custom application metrics (errors, auth failures)
#
# Usage:
#   terraform init
#   terraform plan
#   terraform apply
#
# Prerequisites:
#   - AWS credentials configured
#   - ECS cluster and services already deployed
#   - SNS topic for notifications
# =============================================================================

variable "environment" {
  description = "Environment name (production, staging)"
  type        = string
  default     = "production"
}

variable "sns_alert_topic_arn" {
  description = "SNS Topic ARN for alarm notifications"
  type        = string
}

variable "ecs_cluster_name" {
  description = "ECS Cluster name"
  type        = string
  default     = "oncolife-cluster"
}

variable "patient_api_service" {
  description = "Patient API ECS Service name"
  type        = string
  default     = "patient-api"
}

variable "doctor_api_service" {
  description = "Doctor API ECS Service name"
  type        = string
  default     = "doctor-api"
}

variable "alb_arn_suffix" {
  description = "ALB ARN suffix for metrics"
  type        = string
}

variable "patient_target_group_suffix" {
  description = "Patient API target group ARN suffix"
  type        = string
}

variable "doctor_target_group_suffix" {
  description = "Doctor API target group ARN suffix"
  type        = string
}

variable "rds_instance_identifier" {
  description = "RDS instance identifier"
  type        = string
  default     = "oncolife-db"
}

locals {
  alarm_prefix = "OncoLife-${var.environment}"
}

# =============================================================================
# ECS Service Alarms - Patient API
# =============================================================================

# CPU Utilization High
resource "aws_cloudwatch_metric_alarm" "patient_api_cpu_high" {
  alarm_name          = "${local.alarm_prefix}-PatientAPI-CPU-High"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Patient API CPU utilization is above 80% for 3 minutes"
  
  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.patient_api_service
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Service     = "patient-api"
    Severity    = "warning"
  }
}

# Memory Utilization High
resource "aws_cloudwatch_metric_alarm" "patient_api_memory_high" {
  alarm_name          = "${local.alarm_prefix}-PatientAPI-Memory-High"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Patient API memory utilization is above 80% for 3 minutes"
  
  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.patient_api_service
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Service     = "patient-api"
    Severity    = "warning"
  }
}

# No Running Tasks (Critical)
resource "aws_cloudwatch_metric_alarm" "patient_api_no_tasks" {
  alarm_name          = "${local.alarm_prefix}-PatientAPI-NoRunningTasks"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 60
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "CRITICAL: Patient API has no running tasks!"
  
  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.patient_api_service
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Service     = "patient-api"
    Severity    = "critical"
  }
}

# =============================================================================
# ECS Service Alarms - Doctor API
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "doctor_api_cpu_high" {
  alarm_name          = "${local.alarm_prefix}-DoctorAPI-CPU-High"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Doctor API CPU utilization is above 80% for 3 minutes"
  
  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.doctor_api_service
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Service     = "doctor-api"
    Severity    = "warning"
  }
}

resource "aws_cloudwatch_metric_alarm" "doctor_api_memory_high" {
  alarm_name          = "${local.alarm_prefix}-DoctorAPI-Memory-High"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Doctor API memory utilization is above 80% for 3 minutes"
  
  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.doctor_api_service
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Service     = "doctor-api"
    Severity    = "warning"
  }
}

resource "aws_cloudwatch_metric_alarm" "doctor_api_no_tasks" {
  alarm_name          = "${local.alarm_prefix}-DoctorAPI-NoRunningTasks"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 60
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "CRITICAL: Doctor API has no running tasks!"
  
  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.doctor_api_service
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Service     = "doctor-api"
    Severity    = "critical"
  }
}

# =============================================================================
# Application Load Balancer Alarms
# =============================================================================

# ALB 5xx Error Rate
resource "aws_cloudwatch_metric_alarm" "alb_5xx_errors" {
  alarm_name          = "${local.alarm_prefix}-ALB-5xxErrors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_ELB_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "ALB is returning more than 10 5xx errors per minute"
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Severity    = "error"
  }
}

# Target 5xx Error Rate - Patient API
resource "aws_cloudwatch_metric_alarm" "patient_api_5xx_errors" {
  alarm_name          = "${local.alarm_prefix}-PatientAPI-5xxErrors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Patient API is returning more than 10 5xx errors per minute"
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.patient_target_group_suffix
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Service     = "patient-api"
    Severity    = "error"
  }
}

# Target 5xx Error Rate - Doctor API
resource "aws_cloudwatch_metric_alarm" "doctor_api_5xx_errors" {
  alarm_name          = "${local.alarm_prefix}-DoctorAPI-5xxErrors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Doctor API is returning more than 10 5xx errors per minute"
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.doctor_target_group_suffix
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Service     = "doctor-api"
    Severity    = "error"
  }
}

# High Latency - Patient API
resource "aws_cloudwatch_metric_alarm" "patient_api_high_latency" {
  alarm_name          = "${local.alarm_prefix}-PatientAPI-HighLatency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  extended_statistic  = "p95"
  threshold           = 2  # 2 seconds
  alarm_description   = "Patient API P95 latency is above 2 seconds"
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.patient_target_group_suffix
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Service     = "patient-api"
    Severity    = "warning"
  }
}

# Unhealthy Hosts - Patient API
resource "aws_cloudwatch_metric_alarm" "patient_api_unhealthy_hosts" {
  alarm_name          = "${local.alarm_prefix}-PatientAPI-UnhealthyHosts"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = 0
  alarm_description   = "Patient API has unhealthy targets"
  
  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.patient_target_group_suffix
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Service     = "patient-api"
    Severity    = "error"
  }
}

# =============================================================================
# RDS Database Alarms
# =============================================================================

# Database CPU High
resource "aws_cloudwatch_metric_alarm" "rds_cpu_high" {
  alarm_name          = "${local.alarm_prefix}-RDS-CPU-High"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization is above 80% for 3 minutes"
  
  dimensions = {
    DBInstanceIdentifier = var.rds_instance_identifier
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Severity    = "warning"
  }
}

# Database Connections High
resource "aws_cloudwatch_metric_alarm" "rds_connections_high" {
  alarm_name          = "${local.alarm_prefix}-RDS-Connections-High"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 80  # Adjust based on your instance class
  alarm_description   = "RDS connections are above 80"
  
  dimensions = {
    DBInstanceIdentifier = var.rds_instance_identifier
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Severity    = "warning"
  }
}

# Database Free Storage Low
resource "aws_cloudwatch_metric_alarm" "rds_storage_low" {
  alarm_name          = "${local.alarm_prefix}-RDS-Storage-Low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 5368709120  # 5 GB in bytes
  alarm_description   = "CRITICAL: RDS free storage is below 5 GB"
  
  dimensions = {
    DBInstanceIdentifier = var.rds_instance_identifier
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Severity    = "critical"
  }
}

# Database Read Latency High
resource "aws_cloudwatch_metric_alarm" "rds_read_latency" {
  alarm_name          = "${local.alarm_prefix}-RDS-ReadLatency-High"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "ReadLatency"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 0.02  # 20ms
  alarm_description   = "RDS read latency is above 20ms"
  
  dimensions = {
    DBInstanceIdentifier = var.rds_instance_identifier
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Severity    = "warning"
  }
}

# =============================================================================
# Custom Application Metrics Alarms
# =============================================================================

# High Error Rate
resource "aws_cloudwatch_metric_alarm" "app_error_rate_high" {
  alarm_name          = "${local.alarm_prefix}-Application-ErrorRate-High"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Alert_Error"
  namespace           = "OncoLife/PatientAPI"
  period              = 60
  statistic           = "Sum"
  threshold           = 20
  alarm_description   = "Application error rate is above 20 per minute"
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    Environment = var.environment
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Severity    = "error"
  }
}

# Critical Alerts
resource "aws_cloudwatch_metric_alarm" "app_critical_alerts" {
  alarm_name          = "${local.alarm_prefix}-Application-CriticalAlerts"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Alert_Critical"
  namespace           = "OncoLife/PatientAPI"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "CRITICAL: Application has critical alerts!"
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    Environment = var.environment
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Severity    = "critical"
  }
}

# Authentication Failures High
resource "aws_cloudwatch_metric_alarm" "auth_failures_high" {
  alarm_name          = "${local.alarm_prefix}-AuthFailures-High"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "AuthenticationFailure"
  namespace           = "OncoLife/PatientAPI"
  period              = 60
  statistic           = "Sum"
  threshold           = 50
  alarm_description   = "High rate of authentication failures - possible attack"
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    Environment = var.environment
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Severity    = "warning"
  }
}

# Rate Limit Hits
resource "aws_cloudwatch_metric_alarm" "rate_limit_hits" {
  alarm_name          = "${local.alarm_prefix}-RateLimitHits-High"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RateLimitHit"
  namespace           = "OncoLife/PatientAPI"
  period              = 60
  statistic           = "Sum"
  threshold           = 100
  alarm_description   = "High rate of rate limit hits - possible abuse"
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    Environment = var.environment
  }
  
  alarm_actions = [var.sns_alert_topic_arn]
  ok_actions    = [var.sns_alert_topic_arn]
  
  tags = {
    Environment = var.environment
    Severity    = "warning"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "alarm_arns" {
  description = "List of all alarm ARNs"
  value = [
    aws_cloudwatch_metric_alarm.patient_api_cpu_high.arn,
    aws_cloudwatch_metric_alarm.patient_api_memory_high.arn,
    aws_cloudwatch_metric_alarm.patient_api_no_tasks.arn,
    aws_cloudwatch_metric_alarm.doctor_api_cpu_high.arn,
    aws_cloudwatch_metric_alarm.doctor_api_memory_high.arn,
    aws_cloudwatch_metric_alarm.doctor_api_no_tasks.arn,
    aws_cloudwatch_metric_alarm.alb_5xx_errors.arn,
    aws_cloudwatch_metric_alarm.rds_cpu_high.arn,
    aws_cloudwatch_metric_alarm.rds_storage_low.arn,
  ]
}
