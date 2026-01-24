# Neptune Graph Database Module for AEGIS

variable "project_name" {
  type    = string
  default = "aegis"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "instance_class" {
  type    = string
  default = "db.t3.medium"
}

# Security Group
resource "aws_security_group" "neptune" {
  name_prefix = "${var.project_name}-neptune-"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 8182
    to_port     = 8182
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
    description = "Neptune Gremlin/SPARQL"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-neptune-sg"
    Environment = var.environment
  }
}

# Subnet Group
resource "aws_neptune_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-neptune"
  subnet_ids = var.subnet_ids

  tags = {
    Name        = "${var.project_name}-${var.environment}-neptune-subnet"
    Environment = var.environment
  }
}

# Parameter Group
resource "aws_neptune_cluster_parameter_group" "main" {
  family      = "neptune1.2"
  name        = "${var.project_name}-${var.environment}-neptune-params"
  description = "AEGIS Neptune cluster parameters"

  parameter {
    name  = "neptune_enable_audit_log"
    value = "1"
  }
}

# Neptune Cluster
resource "aws_neptune_cluster" "main" {
  cluster_identifier                  = "${var.project_name}-${var.environment}-neptune"
  engine                              = "neptune"
  backup_retention_period             = 7
  preferred_backup_window             = "02:00-03:00"
  skip_final_snapshot                 = var.environment != "prod"
  iam_database_authentication_enabled = true
  vpc_security_group_ids              = [aws_security_group.neptune.id]
  neptune_subnet_group_name           = aws_neptune_subnet_group.main.name
  neptune_cluster_parameter_group_name = aws_neptune_cluster_parameter_group.main.name
  storage_encrypted                   = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-neptune"
    Environment = var.environment
    HIPAA       = "true"
  }
}

# Neptune Instance
resource "aws_neptune_cluster_instance" "main" {
  count              = var.environment == "prod" ? 2 : 1
  cluster_identifier = aws_neptune_cluster.main.id
  instance_class     = var.instance_class
  engine             = "neptune"

  tags = {
    Name        = "${var.project_name}-${var.environment}-neptune-${count.index + 1}"
    Environment = var.environment
  }
}

# Outputs
output "cluster_endpoint" {
  value = aws_neptune_cluster.main.endpoint
}

output "cluster_reader_endpoint" {
  value = aws_neptune_cluster.main.reader_endpoint
}

output "cluster_port" {
  value = aws_neptune_cluster.main.port
}
