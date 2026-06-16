> Source: apps/showcase/pages/uikit/guide/v3.ts, apps/showcase/doc/uikit/v3/resources-doc.ts, apps/showcase/doc/uikit/v3/tokensets-doc.ts


---

Legacy Notice: UI Kit v3 is deprecated due to its dependency on the Tokens Studio Plugin. We strongly recommend migrating to UI Kit v4, which uses native Figma variables for significantly improved performance and eliminates
                    third-party dependencies.

# PrimeOne Guide

                    PrimeOne is a strong UI component library gets even better with a great Figma UI Kit. That's what PrimeOne is PrimeTek's official Figma UI Kit, built to work seamlessly with the Prime UI Suites.

---

PrimeOne for Figma takes full advantage of powerful Figma features such as components, variants, auto layout, styles, interactivity, and design tokens via Tokens Studio.

        If you're new to Figma or want to get the most out of PrimeOne, we recommend exploring the following resources:

            - Tokens Studio Documentation - PrimeOne uses Tokens Studio for design token management. Visit the official docs to understand how it
                works and how to use it effectively.

            - Figma's Best Practice Guides - Learn how to work efficiently with components, variants, and layouts.

            - Figma's Official YouTube Channel - Tutorials and feature walkthroughs from the Figma team.

            - Figmalion Newsletter  - Stay updated with curated insights from the Figma community.

---

- Primitive
                This set contains the most foundational tokens, such as base colors and border radius, elements that are considered “primitive” by nature.

            - Semantic
                Includes essential system-wide tokens like primary, surface, and other shared design values
                It also defines tokens used across multiple component groups.
                For example, tokens under {form.field.*} are referenced by component-level tokens in InputText, MultiSelect, Checkbox, and other form components, enabling consistent styling across the board.

            - Component
                These tokens are defined specifically for each component to allow deep customization
                While we've aimed to create dedicated tokens for every component state, many of them still reference the semantic or primitive tokens, allowing you to make global updates from a single place when needed.

            - App

                    Tokens in this set are not part of the PrimeUIX system. They are intended for values defined in your own application. The same applies
                    to tokens used in our UI library showcases.

                For example, there is no dedicated font size token in PrimeUIX because font styles are not part of the design system. UI components inherit their font settings from the application.

            - Custom
                If you're using the Figma to Theme feature and want your newly created custom tokens to appear in your Theme Designer themes, place them in this set.

                    Even if you're not using the Theme Designer, we still recommend creating a separate set — or using the existing “Custom” set — for your own tokens. Making changes to the default sets, especially deleting tokens or altering
                    reference values, can lead to inconsistencies with the library tokens and cause additional work during development.
