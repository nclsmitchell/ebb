resource "google_cloud_run_service" "api" {
  template {
    spec {
      containers {
        env {
          name  = "MODEL_ID"
          value = "us.anthropic.claude-3-haiku-20240307-v1:0"
        }
      }
    }
  }
}
