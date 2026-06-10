# Purpose: Variable declarations for the cloudbuild_permissions module.
# Intentionally empty: the IAM bindings in this module hardcode the project number,
# bucket name, AR repo, and SA email as string literals. These values are tied to
# the account-locked production project (project-1f5cbf72-2820-4cdb-949) per the
# Layer A discipline in docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §19. Parameterising
# them would create a path for them to drift, which is exactly what the account
# lock is designed to prevent.
