# V2 - Lambda

# =========
# == ECR ==
# =========

resource "aws_ecr_repository" "api" {
  name                 = "${var.project_name}-api-${var.environment}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = true
  }
}

# ======================
# == Terraform Memory ==
# ======================

resource "aws_s3_bucket" "terraform_state" {
  bucket = "${var.project_name}--terraform-state-${random_id.suffix.hex}"

  #lifecycle {
  #prevent_destroy = true
  #}
}

resource "aws_s3_bucket_versioning" "enabled" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ==============
# == App Data ==
# ==============

resource "aws_s3_bucket" "csv_uploads" {
  bucket = "${var.project_name}-csv-uploads-${var.environment}-${random_id.suffix.hex}"
}

resource "aws_dynamodb_table" "user_movie_stats" {
  name         = "${var.project_name}-stats-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "UserId"

  attribute {
    name = "UserId"
    type = "S"
  }
}

resource "random_id" "suffix" {
  byte_length = 4
}

# ================
# == CloudWatch ==
# ================

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.project_name}-api-${var.environment}"
  retention_in_days = 7
}

# ============
# == Lambda ==
# ============

resource "aws_lambda_function" "api" {
  function_name = "${var.project_name}-api-${var.environment}"
  role          = aws_iam_role.lambda_execution_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.api.repository_url}:latest"
  timeout       = 30
  memory_size   = var.lambda_memory

  environment {
    variables = {
      API_SECRET_KEY = var.api_secret_key
      ENVIRONMENT    = "production"  # Matches your main.py config!
    }
  }
}

# =========================
# == Lambda Function URL ==
# =========================
resource "aws_lambda_function_url" "api_url" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = true
    allow_origins     = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://boxd-metrics.vercel.app"
    ]
    allow_methods     = ["POST"]
    allow_headers     = ["*"]
    expose_headers    = ["keep-alive", "date"]
    max_age           = 86400
  }
}

# =====================
# == Lambda IAM Role ==
# =====================

resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.project_name}-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = "TrustLambda"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "lambda_app_permissions" {
  name        = "${var.project_name}-app-permissions-${var.environment}"
  description = "Allow Lambda to access App Data"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "s3:PutObject",
        "s3:GetObject"
      ]
      Effect = "Allow"
      Resource = [
        "${aws_s3_bucket.csv_uploads.arn}/*"
      ]
    },
    {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.user_movie_stats.arn
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_app_attach" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_app_permissions.arn
}