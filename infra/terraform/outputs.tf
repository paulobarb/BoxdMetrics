output "ecr_repository_url" {
  description = "The URL of ECR repository"
  value       = aws_ecr_repository.api.repository_url
}

output "ecs_cluster_name" {
  description = "The name of ECS Cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "The name of ECS Service"
  value       = aws_ecs_service.api.name
}