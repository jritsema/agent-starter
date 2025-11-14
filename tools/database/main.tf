data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
data "aws_ecr_authorization_token" "token" {}

locals {
  region  = data.aws_region.current.region
  account = data.aws_caller_identity.current.account_id
}

provider "docker" {
  registry_auth {
    address  = "${local.account}.dkr.ecr.${local.region}.amazonaws.com"
    username = data.aws_ecr_authorization_token.token.user_name
    password = data.aws_ecr_authorization_token.token.password
  }
}

resource "aws_dynamodb_table" "records" {
  name         = "${var.name}-records"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    Name = "${var.name}-records"
  }
}

module "lambda_function" {
  source = "terraform-aws-modules/lambda/aws"

  function_name  = var.name
  create_package = false

  image_uri     = module.docker_image.image_uri
  package_type  = "Image"
  architectures = ["arm64"]

  environment_variables = {
    TABLE_NAME = aws_dynamodb_table.records.name
  }
}

data "aws_iam_policy_document" "lambda_dynamodb" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:BatchWriteItem",
      "dynamodb:GetItem",
      "dynamodb:Scan",
      "dynamodb:Query"
    ]
    resources = [aws_dynamodb_table.records.arn]
  }
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name   = "${var.name}-dynamodb-policy"
  role   = module.lambda_function.lambda_role_name
  policy = data.aws_iam_policy_document.lambda_dynamodb.json
}

module "docker_image" {
  source = "terraform-aws-modules/lambda/aws//modules/docker-build"

  create_ecr_repo = true
  ecr_repo        = "${var.name}-database-tool"
  source_path     = "./"
  platform        = "linux/arm64"
}

resource "aws_bedrockagentcore_gateway_target" "database" {
  name               = "${var.name}-target"
  gateway_identifier = var.gateway_id
  description        = "Database tool gateway target"

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = module.lambda_function.lambda_function_arn

        tool_schema {
          inline_payload {
            name        = "put_records"
            description = "Add records to the database"

            input_schema {
              type        = "object"
              description = "Records data to store"

              property {
                name        = "records"
                type        = "array"
                description = "List of records to add"
                required    = true

                items {
                  type = "object"

                  property {
                    name        = "date"
                    type        = "string"
                    description = "Date in YYYY-MM-DD format"
                    required    = true
                  }

                  property {
                    name        = "topic"
                    type        = "string"
                    description = "Topic or subject of the record"
                    required    = true
                  }

                  property {
                    name        = "ranking"
                    type        = "string"
                    description = "Ranking or priority (numeric value as string)"
                    required    = true
                  }

                  property {
                    name        = "description"
                    type        = "string"
                    description = "Detailed description of the record"
                    required    = true
                  }
                }
              }
            }

            output_schema {
              type = "object"

              property {
                name     = "result"
                type     = "string"
                required = true
              }
            }
          }

          inline_payload {
            name        = "get_records"
            description = "Retrieve all records from the database"

            input_schema {
              type        = "object"
              description = "No parameters required"
            }

            output_schema {
              type = "object"

              property {
                name     = "result"
                type     = "string"
                required = true
              }
            }
          }
        }
      }
    }
  }
}
