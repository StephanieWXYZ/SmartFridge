# Deployment

This project is set up for a containerized AWS ECS deployment. The backend API,
Celery worker, and Redis service run as separate ECS services so image processing
and recipe generation do not block normal API requests.

## What Terraform Creates

The Terraform configuration in `backend/terraform` defines:

- an ECS cluster for SmartFridge services
- a FastAPI web service running the backend API
- a Celery worker service running background pipeline tasks
- a Redis service for task messages and results
- a VPC, public and private subnets, security groups, and service discovery
- an application load balancer that exposes the FastAPI web service
- CloudWatch logs for web, worker, and Redis containers

## Required Services

The deployment expects:

- AWS credentials with permission to push images and update ECS services
- ECR repositories named `smartfridge-web` and `smartfridge-worker`
- Terraform-managed ECS services in `backend/terraform`
- OpenAI, Pinecone, and Google API keys for the full AI pipeline
- a Pinecone index matching `PINECONE_INDEX_NAME`

## Release Flow

1. Apply Terraform from `backend/terraform`.

   This creates the ECS cluster, services, Redis service, networking, load balancer,
   and log groups.

2. Configure GitHub Actions secrets.

   The deployment workflow expects `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.
   AI service keys are provided through Terraform variables for the ECS task
   definitions.

3. Run the deployment workflow.

   The workflow in `.github/workflows/deploy.yml` builds the backend Docker image
   twice: once tagged for the web service and once tagged for the worker service.
   It pushes both images to ECR, then forces the ECS web and worker services to
   pull the latest images.

4. Verify the API endpoint.

   Terraform outputs the public FastAPI docs URL as `api_endpoint`.

5. Review CloudWatch logs.

   The web, worker, and Redis log streams should show the API starting, the worker
   connecting to Redis, and task activity when a fridge photo is submitted.

## Operational Considerations

AWS ECS, load balancers, NAT gateways, logs, ECR storage, and AI API calls can cost
money. The workflow is manually triggered so source-code pushes do not automatically
create cloud activity.
