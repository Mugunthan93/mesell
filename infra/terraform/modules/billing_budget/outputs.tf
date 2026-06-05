# Purpose: Outputs for the billing_budget module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10.

output "budget_name" {
  description = "The resource name of the billing budget (projects/<billing_account>/budgets/<id>). Useful for linking to alerting policies or referencing in runbooks."
  value       = google_billing_budget.meesell_dev_budget.name
}
