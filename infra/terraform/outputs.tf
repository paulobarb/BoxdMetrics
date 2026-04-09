output "ecr_repository_url" {
  description = "The URL of ECR repository"
  value       = aws_ecr_repository.api.repository_url
}

#output "lambda_function_name" {
#  description = "The name of the deployed Lambda function"
#  value       = aws_lambda_function.api.function_name
#}

output "s3_csv_bucket_name" {
  description = "The S3 bucket where raw CSVs are uploaded"
  value       = aws_s3_bucket.csv_uploads.id
}