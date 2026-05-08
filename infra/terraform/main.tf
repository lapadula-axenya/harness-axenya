terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  # Remote state — fill in the bucket name from Q2 and uncomment.
  # backend "gcs" {
  #   bucket = "xenia-tfstate"
  #   prefix = "harness"
  # }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.region
}

locals {
  service_prefix = "xenia"
  labels = {
    app  = "xenia-harness"
    env  = var.environment
    team = "axenya-engineering"
  }
}
