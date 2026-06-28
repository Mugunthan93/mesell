## Recurring patterns observed
- Founder's gap descriptions are directionally right but exact mechanics worth verifying — verify the actual code state before quoting the gap shape in a plan
- §11.1 of MVP_ARCHITECTURE is stale on multiple counts (model count: says 8, actually 13; endpoint count: says 20, actually ~25). Treat §3+§7.7+§11.6 as authoritative per founder ruling 2026-06-05
- backend/app/models/ has NO sku.py or image.py — those names were renamed to product.py and product_image.py in the burn-and-rebuild. 4 of 10 routers still import the deleted names
