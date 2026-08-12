resource "null_resource" "config" {
  triggers = {
    model = "gpt-4-turbo"
  }
}
