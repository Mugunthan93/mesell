> Source: apps/showcase/pages/designer/ci.ts, apps/showcase/doc/designer/ci/designerapi-doc.ts, apps/showcase/doc/designer/ci/figma-doc.ts, apps/showcase/doc/designer/ci/livepreview-doc.ts, apps/showcase/doc/designer/ci/overview-doc.ts, apps/showcase/doc/designer/ci/videotutorial-doc.ts


---

UI Kit v4 Users: You may ignore this documentation and use the
                PrimeUI Theme Generator Figma plugin instead, which provides
                built-in synchronization capabilities that automate the theme generation process.

            UI Kit v3 Users: Follow the CI pipeline configuration below to integrate with Figma via the Tokens Studio plugin.

# Figma to Theme Code CI Pipeline (UI Kit v3 Only)

                Automate the conversion of Figma design tokens to theme code using CI pipelines and the theme designer API.

---

Theme Designer public endpoint is hosted at PrimeUI Store.

### Get a Secret Key

            - Visit the PrimeUI Store.

            - Purchase an Extended License of Theme Designer.

            - Navigate to your  account settings.

            - Generate a secret key for CI/CD integration.

### Authentication

        Define a Authentication: Bearer request headerto configure your secret key.

### Parameters

        The request type must be POST.

                | Name
                        | Type
                        | Required
                        | Description

                        | name
                        | string
                        | yes
                        | Name of the theme to be generated.

                        | tokens
                        | json
                        | yes
                        | Content of the json file exported from Figma.

                        | project
                        | string
                        | yes
                        | Name of the project, possible values are "primeng" or "primevue".

                        | config.font_size
                        | string
                        | no
                        | Font size for theme preview in visual editor at website, defaults to "14px".

                        | config.font_family
                        | string
                        | no
                        | Font family for theme preview in visual editor at website, defaults to "Inter Var"

### Example

### Response

        A successful response returns a zip file containing the source code of the generated theme preset. The content-type header of this type of response is application/zip.

### Error Handling

        When theme generation fails, a json response is returned with application/json content-type header. The response contains an error object with code and message.

---

Tokens Studio in Figma is the starting point of a continuous integration pipeline. You can connect a remote repository to sync your tokens data so that changes are saved remotely instead of locally. Tokens Studio offers various remote
            storage options such as GitHub,
            GitLab and
            Bitbucket. Refer to these documentations based on your environment before proceeding to the integrations in the
            next section.

---

After your CI pipeline completes successfully, your theme also becomes available in the Prime UI Theme Designer.

            - Navigate to the Prime UI library website.

            - Click the ⚙️ icon at topbar to open up Designer Editor.

            - Sign in with your license key and pass key credentials.

            - Then select your theme from the available options to apply it across all demos and website content.

            - Note that CI-generated themes are provided in read-only mode for preview purposes only and cannot be edited within the Theme Designer. The Migration Assistant is available to identify any missing tokens in your preset; however, if
                tokens are missing, they must be added manually in Figma as needed.

---

The Figma UI Kit and the theming api is fully synchorized, meaning the design tokens in Figma map to the corresponding properties in a theme preset. The Theme Designer offers a feature to create a theme by uploading a tokens.json file
            that is exported from the Tokens Studio plugin in Figma. Once the theme is converted, it can either be edited further in the visual editor or downloaded as a zip file to access the full code. Visit the
            Figma
            section at the designer documentation for more information.

            Manually exporting the tokens file from Figma and uploading it to the online designer tool may quickly become tedious in active development cycles. As a solution, theme designer provides a remote API that can be integrated into your CI
            pipeline.

---

Before diving into the implementation details, if you would like to understand the final outcome and see how the solution operates, please refer to the video tutorial for a comprehensive walkthrough and demonstration.
