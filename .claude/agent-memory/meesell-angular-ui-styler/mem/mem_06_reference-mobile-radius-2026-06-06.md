## reference: mobile_radius (2026-06-06)

The shell sidebar-card border-radius was changed from 12px → 16px.
This is DESKTOP-ONLY. The `.sidebar-mobile .sidebar-card` rule sets `border-radius: 0`
for mobile — that rule was left unchanged. No mobile layout regression.
The 360px layout is unaffected because mobile uses the overlay drawer (border-radius: 0).

---
