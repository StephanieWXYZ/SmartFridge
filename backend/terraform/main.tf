terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "openai_api_key" {
  type      = string
  sensitive = true
}

variable "pinecone_api_key" {
  type      = string
  sensitive = true
}

variable "google_api_key" {
  type      = string
  sensitive = true
}

variable "pinecone_index_name" {
  type    = string
  default = "fridge-ai-recipes"
}

data "aws_ecr_repository" "web" {
  name = "smartfridge-web"
}

data "aws_ecr_repository" "worker" {
  name = "smartfridge-worker"
}

resource "aws_iam_role" "ecs_execution_role" {
  name = "SmartFridge-Execution-Role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "SmartFridge-VPC"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = false
}

resource "aws_security_group" "web" {
  name        = "SmartFridge-Web-SG"
  description = "Allow inbound HTTP traffic to FastAPI"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "worker" {
  name        = "SmartFridge-Worker-SG"
  description = "Allow outbound traffic from Celery worker"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "redis" {
  name        = "SmartFridge-Redis-SG"
  description = "Allow Redis access from web and worker services"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.web.id, aws_security_group.worker.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecs_cluster" "main" {
  name = "SmartFridge-Cluster"
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/smartfridge"
  retention_in_days = 7
}

resource "aws_service_discovery_private_dns_namespace" "main" {
  name = "smartfridge.local"
  vpc  = module.vpc.vpc_id
}

resource "aws_service_discovery_service" "redis" {
  name = "redis"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 60
      type = "A"
    }
  }
}

locals {
  app_environment = [
    {
      name  = "REDIS_URL"
      value = "redis://redis.smartfridge.local:6379/0"
    },
    {
      name  = "OPENAI_API_KEY"
      value = var.openai_api_key
    },
    {
      name  = "PINECONE_API_KEY"
      value = var.pinecone_api_key
    },
    {
      name  = "PINECONE_INDEX_NAME"
      value = var.pinecone_index_name
    },
    {
      name  = "GOOGLE_API_KEY"
      value = var.google_api_key
    }
  ]
}

resource "aws_ecs_task_definition" "web" {
  family                   = "smartfridge-web-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn

  container_definitions = jsonencode([{
    name      = "smartfridge-web"
    image     = "${data.aws_ecr_repository.web.repository_url}:latest"
    essential = true
    command   = ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]
    environment = local.app_environment
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.app.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "web"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "smartfridge-worker-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn

  container_definitions = jsonencode([{
    name        = "smartfridge-worker"
    image       = "${data.aws_ecr_repository.worker.repository_url}:latest"
    essential   = true
    command     = ["celery", "-A", "app.worker.celery_app", "worker", "--loglevel=info"]
    environment = local.app_environment
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.app.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "worker"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "redis" {
  family                   = "smartfridge-redis-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn

  container_definitions = jsonencode([{
    name      = "smartfridge-redis"
    image     = "redis:7-alpine"
    essential = true
    portMappings = [{
      containerPort = 6379
      protocol      = "tcp"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.app.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "redis"
      }
    }
  }])
}

resource "aws_ecs_service" "redis" {
  name            = "smartfridge-redis-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.redis.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.redis.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.redis.arn
  }
}

resource "aws_lb" "main" {
  name               = "SmartFridge-ALB"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.web.id]
  subnets            = module.vpc.public_subnets
}

resource "aws_lb_target_group" "web" {
  name        = "SmartFridge-Web-TG"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  health_check {
    path = "/docs"
    port = "8000"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

resource "aws_ecs_service" "web" {
  name            = "smartfridge-web-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = module.vpc.public_subnets
    security_groups  = [aws_security_group.web.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "smartfridge-web"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.http]
}

resource "aws_ecs_service" "worker" {
  name            = "smartfridge-worker-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.worker.id]
    assign_public_ip = false
  }
}

output "api_endpoint" {
  value       = "http://${aws_lb.main.dns_name}/docs"
  description = "Public URL for the SmartFridge FastAPI documentation."
}
