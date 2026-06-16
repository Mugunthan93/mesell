> Source: apps/showcase/pages/uikit/guide/v4.ts, apps/showcase/doc/uikit/v4/collections-doc.ts, apps/showcase/doc/uikit/v4/importantnotice-doc.ts, apps/showcase/doc/uikit/v4/limitations-doc.ts, apps/showcase/doc/uikit/v4/primeuifigmaplugin-doc.ts, apps/showcase/doc/uikit/v4/resources-doc.ts


---

# PrimeOne Guide | 4.0

                    PrimeOne is a strong UI component library gets even better with a great Figma UI Kit. That's what PrimeOne is PrimeTek's official Figma UI Kit, built to work seamlessly with the Prime UI Suites.

---

- Primitive
                This collection contains the most foundational variables, such as base colors and border radius, elements that are considered “primitive” by nature.

            - Semantic Common & Semantic Color Scheme

                    Includes essential system-wide variables like primary, surface, and other shared design values It also defines variables used across multiple component groups. For example, variables under form/field are referenced by
                    component-level variables in InputText, MultiSelect, Checkbox, and other form components, enabling consistent styling across the board.

            - Component Common & Component Color Scheme

                    These variables are defined specifically for each component to allow deep customization. While we've aimed to create dedicated variables for every component state, many of them still reference the semantic or primitive variables,
                    allowing you to make global updates from a single place when needed.

            - App

                    Variables in this collection are not part of the PrimeUIX system. They are intended for values defined in your own application. The
                    same applies to variables used in our UI library showcases. For example, there is no dedicated font size variable in PrimeUIX because font styles are not part of the design system. UI components inherit their font settings
                    from the application.

            - Custom

                    If you're using the Figma to Theme feature and want your newly created custom variables to appear in your Theme Designer themes, place them in this collection. Even if you're not using the Theme Designer, we still recommend
                    creating a separate collection — or using the existing “Custom” collection — for your own variables. Making changes to the default collections, especially deleting variables or altering reference values, can lead to
                    inconsistencies with the library variables and cause additional work during development.

---

Starting from PrimeOne UI Kit version 4.0, the Tokens Studio plugin is no longer used. We've fully migrated to Figma's native variable features, which now power the system. If you prefer to continue working with Tokens Studio, please use
            PrimeOne UI Kit version 3.2, which still supports the plugin.

---

Current known technical limitations are listed at this section.

            - Multiple-value variables - Figma currently supports only a single value per variable. For this reason, multi-value tokens defined in PrimeUIX—such as padding or margin, which can contain multiple values—are represented in Figma
                as separate variables for each side (top/right/bottom/left) or axis (x/y), unlike the combined multi-value CSS definitions in PrimeUIX.

            - Calculations - Since Figma does not yet allow calculations within variable definitions, values that rely on expressions like calc() cannot function dynamically. In these cases, any adjustments you make may require manual
                updates.

            - Focus Rings - In Tokens Studio, focus rings could be positioned by calculating the outer stroke distance using expressions such as focus.ring.width + focus.ring.offset. Since Figma Variables do not support arithmetic
                operations, these calculations cannot be reproduced. As a result, focus ring width values are no longer dynamically linked and must be handled as static values.

            - Color Mix - Figma Variables do not currently support color mix modifiers. Values in PrimeUIX that rely on color mixing have therefore been converted into raw hex values when brought into Figma Variables.

---

PrimeUI Theme Generator Figma plugin is the official tool developed by PrimeTek that provides built-in synchronization capabilities to automate the theme code generation process. Visit the
            plugin website to learn more about this workflow.

---

PrimeOne for Figma takes full advantage of powerful Figma features such as components, variants, auto layout, styles, prototypes, and variables.

        If you're new to Figma or want to get the most out of PrimeOne, we recommend exploring the following resources:

            - Variables - PrimeOne uses Figma Variables for design token management. Visit the official docs
                to understand how it works and how to use it effectively.

            - Figma's Best Practice Guides - Learn how to work efficiently with components, variants, and layouts.

            - Figma's Official YouTube Channel - Tutorials and feature walkthroughs from the Figma team.

            - Figmalion Newsletter  - Stay updated with curated insights from the Figma community.
