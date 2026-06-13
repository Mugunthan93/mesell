"""Versioned prompt template registry — §6A.G.

Resolves a ``prompt_id`` like ``"smart_picker.v1"`` or ``"autofill.v2"``
to a :class:`PromptTemplate` by dynamic-importing
``app.ai_ops.prompts.<name>_v<version>``.

V1 active versions (locked):

* ``smart_picker.v1`` → :mod:`app.ai_ops.prompts.smart_picker_v1`
* ``autofill.v1``     → :mod:`app.ai_ops.prompts.autofill_v1`
* ``watermark.v1``    → :mod:`app.ai_ops.prompts.watermark_v1`

Each prompt module is expected to expose two module-level constants:

* ``TEMPLATE: str``     — Jinja2-style with ``{{var}}`` placeholders.
  Owned by :mod:`meesell-prompt-engineer` per §6A.G.
* ``VERSION: str``      — ``"v1"``, ``"v2"``, ...
* ``WORKLOAD: str``     — must match the workload literal.
* ``RENDERED_BY: str``  — ``"text"`` or ``"vision"``.

V1.5 active-version dispatch via Valkey config flag
``meesell:ai_ops:active_version:{workload}`` is deferred per §6A.G —
V1 ships hardcoded resolution.

Rendering
---------
The template uses simple ``{{var}}`` substitution; no Jinja2 dependency
is added for V1.  :func:`render` does a literal ``str.replace`` for each
key in ``prompt_vars``.  This is sufficient for V1's flat-variable
templates; V1.5 may upgrade to Jinja2 if conditionals/loops are needed.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from typing import Any, Literal

from app.ai_ops.cost_tracker import Workload

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PromptTemplate:
    """Resolved prompt template — see §6A.G."""

    template: str
    version: str
    workload: str
    rendered_by: Literal["text", "vision"]


class PromptResolutionError(Exception):
    """Raised when ``prompt_id`` cannot be resolved to a prompt module."""


def resolve(prompt_id: str, workload: Workload) -> PromptTemplate:
    """Resolve ``prompt_id`` to a :class:`PromptTemplate`.

    Per §6A.G.

    Args:
        prompt_id: Dotted reference of the form ``"<name>.v<version>"``,
            e.g. ``"smart_picker.v1"`` or ``"autofill.v2"``.
        workload: The 3-workload literal — verified against the loaded
            module's ``WORKLOAD`` constant.  Mismatch raises
            :class:`PromptResolutionError`.

    Returns:
        :class:`PromptTemplate` with the template body and metadata.

    Raises:
        PromptResolutionError: ``prompt_id`` is malformed; the prompt
            module is missing; the workload does not match; or the
            module is missing one of the required constants.
    """
    name, version = _parse_prompt_id(prompt_id)
    module_name = f"app.ai_ops.prompts.{name}_{version}"
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise PromptResolutionError(
            f"Prompt module not found for prompt_id={prompt_id!r}: {module_name}"
        ) from exc

    try:
        template = module.TEMPLATE
        mod_version = module.VERSION
        mod_workload = module.WORKLOAD
        mod_rendered_by = module.RENDERED_BY
    except AttributeError as exc:
        raise PromptResolutionError(
            f"Prompt module {module_name} missing one of "
            f"(TEMPLATE, VERSION, WORKLOAD, RENDERED_BY): {exc}"
        ) from exc

    if mod_workload != workload:
        raise PromptResolutionError(
            f"Prompt {prompt_id!r} declares workload={mod_workload!r} but "
            f"caller requested workload={workload!r}"
        )
    if mod_rendered_by not in ("text", "vision"):
        raise PromptResolutionError(
            f"Prompt {prompt_id!r} RENDERED_BY must be 'text' or 'vision', "
            f"got {mod_rendered_by!r}"
        )

    return PromptTemplate(
        template=template,
        version=mod_version,
        workload=mod_workload,
        rendered_by=mod_rendered_by,
    )


def render(template: str, prompt_vars: dict[str, Any]) -> str:
    """Substitute ``{{var}}`` placeholders.  V1 flat-variable only.

    Missing placeholders are left as-is (no silent empty-string
    substitution) so a debugging eye sees the unresolved variable.
    """
    out = template
    for key, value in prompt_vars.items():
        out = out.replace("{{" + key + "}}", str(value))
    return out


def _parse_prompt_id(prompt_id: str) -> tuple[str, str]:
    """Split ``"<name>.v<n>"`` into ``("<name>", "v<n>")``.

    Raises :class:`PromptResolutionError` on malformed input.
    """
    if "." not in prompt_id:
        raise PromptResolutionError(
            f"prompt_id must be of form '<name>.v<n>', got {prompt_id!r}"
        )
    name, _, version = prompt_id.rpartition(".")
    if not name:
        raise PromptResolutionError(
            f"prompt_id must have a name segment before the version, got {prompt_id!r}"
        )
    if not version.startswith("v") or not version[1:].isdigit():
        raise PromptResolutionError(
            f"prompt_id version segment must match 'v<int>', got {version!r}"
        )
    return name, version


__all__ = [
    "PromptResolutionError",
    "PromptTemplate",
    "render",
    "resolve",
]
