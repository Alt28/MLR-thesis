# Research-tool interface

The local React interface uses a dark charcoal workspace, mint accents, and Manrope typography. Dark mode is the default, including native form controls, search, dialogs, tables, and status messages. Research pages and API calculations retain their existing behavior.

Typography adjustment: the Analyze stylesheet uses relative font sizes, with a 14 px body/control baseline and a 13 px minimum for supporting labels and table explanations at the default browser font setting. Secondary text has stronger contrast. Desktop retains the dataset/results columns; narrower screens stack the panels and allow navigation and prediction values to wrap instead of reducing text size. Shared dialogs, form controls, and full tables follow the same scale.

Chart previews use a matching dark Matplotlib palette. Downloaded PNGs and the experiment bundle retain the original light figures for reports. Dark previews are cached separately from the exported artifacts; no scientific values are changed.

## Navigation and feedback

- Two links: **Analyze** and **About / Methodology**. No sidebar, dashboard, page-search menu, management pages, or visible experiment history.
- Desktop: dataset on the left and analysis results on the right. Mobile: the same sections stack without page-level horizontal overflow; wide tables scroll within their containers.
- Dataset validation appears beside the input. The primary action is **Analyze Dataset**, disabled until there is a valid dataset and while work is running.
- The workflow asks for explicit interaction approval only when needed, and opens IQR review when flagged observations have no recorded decision. It never automatically deletes flags.
- The main result shows Predicted Waiting Time, Station Condition, and Model Accuracy (enhanced RMSE) only. View Predictions is directly available on the main result. View Details opens supporting evidence; Export Results downloads the results. Advanced Settings remains collapsed.
- **Export Results** is one entry point for Excel, CSV, and the complete reproducibility bundle. It does not require another route.
- Native dialogs have accessible titles, Escape dismissal, and focus return to the opening control. Buttons use brief hover/press feedback. Dialogs, disclosures, and newly available results use short fade/slide transitions. Reduced-motion preferences are respected.
- No metric or plot appears before a completed analysis. Undefined classifications display **Requires Researcher Decision**.
- The new interface was visually checked on desktop and mobile. See [SIMPLIFICATION_REVIEW.md](SIMPLIFICATION_REVIEW.md) for the thesis comparison and preserved functionality.

## Main result and optional details

The existing dataset panel, navigation, dark palette, and compact typography are retained. A lightly tinted teal-to-charcoal summary, restrained clock/gauge icons, fine dividers, and grouped actions make the result easier to scan. No new navigation or management features are introduced.

The main panel shows the enhanced **Predicted Waiting Time** (38 px desktop, 34 px mobile), **Station Condition**, and **Model Accuracy** as enhanced RMSE rounded to two decimals in minutes. The observation ID identifies which record the result describes. Negative predictions retain their raw value and a brief pointer to the explanation. Undefined classifications remain **Requires Researcher Decision**. No sample values or confidence percentages are fabricated.

**View Details** opens an accessible dialog in this order:

1. **Summary** explains the selected observation's wait and condition in plain language. Unresolved factors are explained here, inside the dialog only.
2. **Model Performance** compares Traditional and Enhanced MLR using a small MSE/RMSE table. Short explanations distinguish minutes of error from confidence percentages.
3. **Prediction Details** shows actual wait, both predictions, their errors, for the selected observation.
4. **Advanced Research Details**, collapsed by default, contains station scoring, coefficients/intercepts, IQR calculations, training quartiles, interaction specifications, encoding, research tables, and charts. Technical table requests start only when expanded.

Inside Advanced Research Details, **View Threshold Details** contains all seven factors, training-derived mappings or explicit overrides, category means, saved training quartiles, direction/source, severity scores, the score formula, and classification ranges. Constant factors display Insufficient Variation for Classification with a blank score. Changing the observation updates both the dialog and main summary. Research calculations and exported artifacts retain their backend values.

**Export Results** remains directly available beside View Details. Dialogs support Escape and return focus to their opening buttons. The prediction dialog returns focus to View Predictions on the main screen. Wide tables scroll inside their containers on smaller screens. Main summary labels and numerical results share the same backend outputs used in the detailed explanation.

## Guided workflow and loading

The Analyze introduction identifies Upload Dataset, Analyze, View Prediction, and View Station Condition. Before upload, the results panel explains the next action; after upload it points to Analyze Dataset. The dataset panel keeps file information, validation, a three-row preview, and its primary action.

Analysis disables the primary button and shows a spinner with useful status text. The loading panel describes the work included (data preparation, prediction, evaluation, station condition); these are not simulated progress steps or percentages. Completion follows the server response and automatically scrolls to results when they are below the viewport. Reduced-motion users receive immediate transitions.

Missing-column messages name the required column(s), while unreadable files and connection failures give actionable guidance. Raw analysis errors remain available in a collapsed disclosure. Required researcher approval and unusual-observation review retain their existing behavior. Confirmation controls cannot be submitted repeatedly while the request is pending.

## Web references consulted

1. [Google Material Design: buttons](https://m3.material.io/components/buttons/overview) and its [official Material Web documentation on GitHub](https://github.com/material-components/material-web/blob/main/docs/components/button.md). References for filled, outlined, and text-action hierarchy, descriptive labels, icons, and focus states. The project uses its own CSS and existing React controls, rather than importing Material components.
2. [Google Material Design: navigation drawers](https://m2.material.io/develop/android/components/navigation-view/). Consulted for the earlier interface. The current simplification removes the drawer and uses two navigation links.
3. [IBM Carbon: motion](https://www.carbondesignsystem.com/building-blocks/foundations/motion/overview). Reference for brief, purposeful feedback, easing, and reduced-motion alternatives.
4. [Google Fonts: Manrope](https://github.com/google/fonts/tree/main/ofl/manrope). The variable font is stored locally in `frontend/src/assets/` and bundled into the app. The SIL Open Font License is included in `frontend/public/fonts/OFL-Manrope.txt` and the compiled distribution. No remote font service is needed at runtime.

These are interface design and asset references, not evidence for the thesis's statistical claims.


## Horizontal table navigation

Wide prediction, dataset, and research tables support grabbing and dragging left/right with a mouse from any non-interactive cell or heading. A grab cursor and short hint appear when columns overflow. Touch swiping, trackpads, the native scrollbar, and keyboard arrow navigation remain available. Observation buttons keep their usual behavior; dragging does not select an observation. The shared component changes navigation only, not table values or research calculations.


## Result placement and observation access

The main result starts with the selected observation ID. Waiting time and station condition sit side by side on wider screens, with model accuracy in a smaller row beneath. Narrow screens stack these values. **View Predictions** is the primary result action; View Details and Export Results remain secondary. View Predictions opens the searchable prediction table directly, without opening research details first.

Selecting a record updates the waiting time, station condition, and selected ID together. The result sections use a short, staggered fade/slide on arrival and observation changes; displayed numbers are always the actual saved values. Reduced-motion preferences disable these transitions. Research details retain prediction errors, comparison, and collapsed technical evidence, without duplicating the observation controls.


The analysis loading state displays a small mint bus sticker with a gentle bobbing motion above the loading message. It is decorative and hidden from assistive technology; the loading text announces the analysis status. The sticker disappears when results arrive, with no progress bar or completion banner. Reduced-motion preferences keep the sticker still. No artificial delay is added.


## Controlled thesis experiments

The dataset badge says Format valid to distinguish column/type validation from research validity. A compact source notice identifies declared prototype data or undocumented origins. Advanced Settings > Research documentation records source and method rationale without claiming independent verification. View Details > Model Performance offers a collapsed three-arm comparison (A original Traditional, B reviewed Traditional, C reviewed Enhanced), while the existing main comparison stays B/C. Research table and export menus include original-model checks, all three predictions, and source documentation. The bus loader, main result hierarchy, and seven-factor classification behavior remain intact.


## Bus and train output views

[Rush PH](https://rush-ph.com/) and its transport-line view informed the segmented Bus/Train controls, service icons, and route/station context. Transit Lab retains its dark theme. Bus results use mint accents; train results use soft violet accents. Results are dataset predictions, with no live-arrival claim.

All, Bus, and Train filter the same saved test predictions. Unspecified appears for missing or unrecognized mode labels. View Predictions follows the active filter; selecting a row updates its wait, condition, and available route/station labels. An empty mode shows an explanation rather than another mode's result. Overall RMSE remains across all test observations. Exports include the entire experiment.

Single-mode files can be labeled using Set transport mode beside the dataset. Mixed files require a Transport Mode column. Row metadata takes precedence over a dataset declaration. Saving a declaration invalidates results through the existing revision workflow. Labels do not enter the six-predictor regression or create separate fitted models. Responsive context labels keep mobile results readable; existing result transitions respect reduced motion.


## Cloud dataset import

A secondary cloud-download button sits immediately beneath the local upload area. Its dialog contains a provider selector, sharing-link field, supported-file guidance, and local-copy explanation. Downloading/checking uses an indeterminate spinner with disabled controls; it does not fabricate progress. Validation failures remain visible in the dialog for correction, while a successful import closes it and restores the normal Analyze workflow. Existing dark colors, dialog motion, keyboard focus, and research logic remain intact.

This is shared-link import, not OAuth account integration. Google Drive and personal OneDrive CSV/XLSX files must be downloadable without signing in; Google Sheets, folders, and business accounts are excluded. Provider documentation consulted: [Google Drive downloads](https://developers.google.com/workspace/drive/api/guides/manage-downloads) and [Microsoft shared-item access](https://learn.microsoft.com/en-us/graph/api/shares-get). These documents describe provider download/access constraints; they are not guarantees that every anonymous sharing URL permits a download.


## Dataset layout cleanup

Local upload and cloud import share one compact area, with template downloads in a disclosure. The file name has its own full-width row; observation count and validation no longer compete for its space. Format validity remains distinct from research provenance. A visible source-status disclosure retains the prototype/undocumented warning while hiding the longer explanation until requested. Transport metadata sits with the file information.

View Full Dataset sits beside the preview heading. Advanced Settings actions use an aligned grid, cloud import uses a narrower form dialog, and modal footer buttons can wrap. Mobile import buttons stack to avoid cramped labels; filename wrapping preserves the entire name. Existing typography, dark colors, result hierarchy, calculations, and interaction behavior remain intact.


## Driving bus loading animation

The loading sticker is replaced by a small locally bundled SVG bus with rotating wheel spokes, gentle suspension motion, moving road markings, and subtle speed lines. It appears only while analysis is pending; completion removes the scene immediately without an artificial delay or progress percentage. The existing status text remains accessible, while the decorative scene is hidden from assistive technology. Reduced-motion preferences stop both the CSS scene and the SVG wheel animations.

Asset: Microsoft Fluent Emoji [Bus, Flat](https://github.com/microsoft/fluentui-emoji/blob/main/assets/Bus/Flat/bus_flat.svg), fetched 5 November 2026, upstream Git blob f671a6dafeef4c0c8ffcd54e5b5d80d5add17b2a. Adaptations: mint/dark palette, cropped viewBox, animated wheel spokes, and CSS driving scene. The upstream MIT copyright/license is included in frontend/public/fonts/LICENSE-Fluent-Emoji.txt and the compiled distribution. No runtime GitHub request or animation library is needed.


## Classification in the prediction table

View Predictions now starts with Record ID, Enhanced Predicted Waiting Time, Station Condition, and Multi-Factor Score (0-3), followed by metadata, actual wait, Traditional prediction, and errors. This makes Solution 3 visible for every listed test observation. The same saved seven-factor label and score are used in the summary, table, and detailed breakdown. Pending classifications retain Requires Researcher Decision and a blank score. A short explanation distinguishes the combined score from waiting-time severity. Main-screen technical details remain collapsed.
