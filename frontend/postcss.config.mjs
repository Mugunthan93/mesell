// NOTE: This file is NOT used by @angular/build:application.
// Angular only reads postcss.config.json or .postcssrc.json.
// The actual PostCSS config used by Angular is postcss.config.json.
// This file exists for tooling compatibility (e.g., direct `npx tailwindcss` CLI runs).
export default {
  plugins: {
    "@tailwindcss/postcss": {
      base: new URL(".", import.meta.url).pathname,
    },
  },
};
