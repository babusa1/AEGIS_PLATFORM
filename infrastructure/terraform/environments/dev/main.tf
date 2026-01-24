# AEGIS Development Environment

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "aegis-terraform-state"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "aegis-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "aegis"
      Environment = "dev"
      ManagedBy   = "terraform"
      HIPAA       = "true"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

# VPC
module "vpc" {
  source = "../../modules/vpc"

  project_name       = "aegis"
  environment        = "dev"
  vpc_cidr           = "10.0.0.0/16"
  availability_zones = ["us-east-1a", "us-east-1b"]
}

# Neptune Graph Database
module "neptune" {
  source = "../../modules/neptune"

  project_name   = "aegis"
  environment    = "dev"
  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_subnet_ids
  instance_class = "db.t3.medium"
}

# MSK (Kafka)
module "msk" {
  source = "../../modules/msk"

  project_name  = "aegis"
  environment   = "dev"
  vpc_id        = module.vpc.vpc_id
  subnet_ids    = module.vpc.private_subnet_ids
  instance_type = "kafka.t3.small"
}

# ECS Cluster
module "ecs" {
  source = "../../modules/ecs"

  project_name       = "aegis"
  environment        = "dev"
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  public_subnet_ids  = module.vpc.public_subnet_ids
}

# Outputs
output "vpc_id" {
  value = module.vpc.vpc_id
}

output "neptune_endpoint" {
  value     = module.neptune.cluster_endpoint
  sensitive = true
}

output "kafka_brokers" {
  value     = module.msk.bootstrap_brokers_tls
  sensitive = true
}

output "ecs_cluster" {
  value = module.ecs.cluster_name
}

output "alb_dns" {
  value = module.ecs.alb_dns_name
}
