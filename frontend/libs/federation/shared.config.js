// Canonical Native Federation shared-libs map for ALL MeeSell federation configs.
// Single source of truth — required by apps/shell + apps/mfe-* federation.config.js.
// WHY (Step 3A): the mesellShared block was duplicated inline across 8 configs; mfe-billing
// was added (Wave 5) WITHOUT the pin -> drift = the #328 shell->remote singleton-logout class.
// DO NOT WEAKEN: singleton:true + strictVersion:true + version/requiredVersion='1.0.0' on the
// 4 cross-boundary libs is the #328 fix. @mesell/layout + @mesell/design-tokens are intentionally
// NOT pinned. Spread this AFTER shareAll(...) so the pins win.
const MESELL_SHARED_VERSION = '1.0.0';
const mesellShared = {
  '@mesell/core':      { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/env':       { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/ui-kit':    { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/composites': { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
};
module.exports = { MESELL_SHARED_VERSION, mesellShared };
