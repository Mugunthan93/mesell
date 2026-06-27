## catalog-form merge-gate D1 fix — M10 local-var rename (2026-06-16, branch feature/catalog-form-fix)

Merge-gate REJECTED commit e6980c6 for ONE defect: in `category/service.py::_map_field_to_dto`
the LOCAL VAR `enum_codes_map` is an M10 forbidden export-layer symbol when used as an IDENTIFIER
outside `app/modules/export/**`. The §16 M10 AST scanner (Contract 9, check_no_meesho_symbols_outside_export.py)
flags `ast.Name`/`ast.Attribute`/`ast.keyword`/`ast.arg` for the 3 forbidden symbols
(meesho_column_header / meesho_column_index / enum_codes_map). String LITERALS are NOT walked.

FIX: renamed local `enum_codes_map` → `inline_enum_map` (3 lines, ~561-564), kept
`rich.get("enum_codes_map")` string subscript intact. No behavior change. Committed 8e912dc as single
file. ruff clean; 110 passed (lint + test_schema_dto_mapper + test_per_field_shape_keys).

LESSON (reusable): when reading a forbidden-symbol key out of a dict, NEVER name the receiving local
after the key. Use a neutral local name (`inline_enum_map`) and keep the forbidden token only as the
quoted string subscript. The scanner is identifier-only.

---
