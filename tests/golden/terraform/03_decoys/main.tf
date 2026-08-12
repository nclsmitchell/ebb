variable "region" {
  default = "us-central1-gpt"
}

resource "aws_s3_bucket" "claude_configs" {
  bucket = "claude-configs-prod"
}
