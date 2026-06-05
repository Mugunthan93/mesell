# Purpose: Variable declarations for the billing_budget module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9, §10.

variable "budget_amount_inr" {
  type        = number
  description = "Monthly budget cap in INR. No default — root must supply this value explicitly. The billing account is INR-denominated; ₹25,000 ≈ $300 free-credit equivalent. Alerts trigger at 50%, 75%, and 90% of spend."
}

variable "display_name" {
  type        = string
  default     = "meesell-dev-budget"
  description = "Human-readable name for the billing budget as it appears in GCP Console. Override in tfvars if a different name is required."
}
