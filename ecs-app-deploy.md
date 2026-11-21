# Deploy the Compose stack to ECS

This CloudFormation stack creates a new VPC and an ECS Fargate cluster in two Availability Zones. It puts an internet-facing Application Load Balancer on port 8080 in front of two Nginx tasks. Nginx discovers Flask tasks through AWS Cloud Map (`web.app.local`); the Flask service starts with two tasks and can be scaled independently. Redis runs as one private-to-the-app ECS service, with `/data` stored on encrypted EFS.

## Before deploying

- Deploy in `ap-southeast-2`, the Region of the supplied ECR image.
- The execution identity needs CloudFormation permissions to create ECS, EC2/VPC, ELB, IAM, Cloud Map, EFS, and CloudWatch Logs resources, and permission to pass the ECS task execution role.
- The ECR repository must allow the ECS task execution role to pull the image. The stack creates a standard ECS execution role; for a cross-account ECR repository, grant that role access in the repository policy.
- The Flask image must contain the application code (the Compose `./app:/app` bind mount is intentionally removed) and listen on `0.0.0.0:5000`. The Flask app should retry Redis connections during startup because ECS cannot order startup across separate services.
- This stack creates public IPv4 addresses for Fargate tasks so they can pull images without a NAT gateway. Security groups permit inbound app traffic only from the preceding tier; only the ALB accepts internet traffic, on HTTP port 8080. Use private subnets plus NAT or VPC endpoints if organizational policy forbids public task addresses.

## Deploy

From a shell with AWS CLI credentials and CloudFormation permissions:

```powershell
aws cloudformation deploy `
  --template-file .\ecs-app-stack.yaml `
  --stack-name diy-py-app `
  --region ap-southeast-2 `
  --parameter-overrides WebDesiredCount=2
```

Get the app URL after the stack finishes:

```powershell
aws cloudformation describe-stacks `
  --stack-name diy-py-app `
  --region ap-southeast-2 `
  --query "Stacks[0].Outputs[?OutputKey=='ApplicationUrl'].OutputValue | [0]" `
  --output text
```

Scale the Flask service by updating `WebDesiredCount` in the deploy command. Replace the `latest` image tag with an immutable tag or digest for repeatable deployments.

## How Compose maps to ECS

| Compose | ECS implementation |
|---|---|
| `nginx` | ECS Fargate service behind an ALB listener on port 8080. The stack writes an Nginx reverse-proxy config at container startup. |
| `web` | Independently scalable Fargate service; Cloud Map DNS name `web.app.local`; Redis address supplied as `REDIS_HOST=redis.app.local`. |
| `redis` | One Fargate task with the `redis:7-alpine` image, AOF enabled, a Redis CLI health check, and `/data` on encrypted EFS. |
| `frontend` / `backend` networks | VPC security groups: internet → ALB → Nginx → Flask → Redis. Redis accepts no inbound traffic from the internet or Nginx. |
| `depends_on` | Redis health check is configured, but ECS services deploy independently; Flask must retry Redis while it starts. Nginx resolves the web service through Cloud Map at runtime. |
| `./app:/app` bind mount | Omitted for deployment. Build the source code into the ECR image; a local source bind mount is not available on Fargate. |
| `redis-data` named volume | Encrypted EFS mounted at `/data`. The EFS file system is retained when the stack is deleted. |

## Operational notes

- Redis is a single task and is not highly available. EFS preserves its files when the task is replaced, but it does not provide Redis replication or failover. For production data durability and automatic failover, use Amazon ElastiCache for Redis OSS/Valkey instead.
- The ALB health check uses Nginx's local `/health` endpoint. Confirm the Flask app's actual health endpoint and add an end-to-end check if desired.
- HTTP is used because no domain name or TLS certificate was provided. Add an HTTPS listener and certificate before exposing sensitive traffic.
- EFS, the ALB, public IPv4 addresses, Fargate tasks, and CloudWatch Logs incur AWS charges. The EFS filesystem has a `Retain` deletion policy, so remove it separately after backing up data if you no longer need it.
