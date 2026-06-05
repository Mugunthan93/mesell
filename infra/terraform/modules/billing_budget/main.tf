# Purpose: GCP billing budget with threshold alerts for the MeeSell project.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9 (module boundaries),
#                 §11 (Pass 1 bootstrap — last module applied), §19.6 (Layer F: free-tier exit).
# Choices:
#   - billing_account is hardcoded (not a variable) per Section 19 Layer A account lock.
#     Passing it as a variable creates an attack surface — a misrouted tfvars could silently
#     apply a budget to the wrong billing account. The literal string is the only safe choice.
#   - provider = google-beta because google_billing_budget is a beta-only resource.
#   - data.google_project.current is used to get the numeric project number required by
#     budget_filter.projects. The string project ID is NOT accepted there — GCP requires
#     the form "projects/<number>".
#   - prevent_destroy = true: deleting this budget would remove the only spending alert,
#     violating the free-credit discipline in §19.6.
#   - Three threshold rules (50%, 75%, 90%) match the playbook §13 gcloud command.

terraform {
  required_providers {
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.30"
    }
  }
}

data "google_project" "current" {
  provider = google-beta
}

resource "google_billing_budget" "meesell_dev_budget" {
  provider = google-beta

  # ACCOUNT LOCK: hardcoded per §19 Layer A — do not parameterise.
  billing_account = "01620D-6785AB-0E4698"
  display_name    = var.display_name

  budget_filter {
    projects = ["projects/${data.google_project.current.number}"]
  }

  amount {
    specified_amount {
      currency_code = "INR"
      units         = tostring(var.budget_amount_inr)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 0.75
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 0.9
    spend_basis       = "CURRENT_SPEND"
  }

  lifecycle {
    prevent_destroy = true
  }
}
