> Historical old-schema teaching material. The current six predictors and pending classification methodology are documented in docs/SIX_PREDICTOR_MIGRATION.md. The figures here have not been recomputed or reinterpreted.

# Illustrated guide to Chapters 3–5

This separate, 35-page study companion explains the highlighted thesis in plain English, with 18 embedded images, worked calculations, figure walkthroughs, a glossary, and defense practice questions.

- [Read the PDF](Chapters_3_to_5_Illustrated_Study_Guide.pdf)
- [Download the editable Word document](Chapters_3_to_5_Illustrated_Study_Guide.docx)
- [Read the text and images on GitHub](Chapters_3_to_5_Illustrated_Study_Guide.md)

The guide preserves the six predictors and the arrival-to-boarding waiting-time definition. Teaching examples are labeled. The Chapter 4 plots reproduce the saved synthetic prototype run; they are not results from recorded Philippine passenger observations. The existing prototype shows no accuracy improvement from its selected interactions.

The original thesis and datasets are unchanged. The source and figure map at the end of the guide identifies the material used.

## Authoring

The text source is [`scripts/chapter_3_to_5_guide_content.md`](../../scripts/chapter_3_to_5_guide_content.md). [`scripts/build_chapter_3_to_5_guide.py`](../../scripts/build_chapter_3_to_5_guide.py) creates the Word document and images in the ignored `outputs/` directory. It requires the original manuscript and figure folder in the author's Downloads directory and the saved prototype run listed in the script. These source inputs are not all included in this folder.

Document generation uses `python-docx`, `matplotlib`, `numpy`, `Pillow`, and `PyMuPDF`. PDF export was performed through Microsoft Word, and the exported 35 pages were checked for section placement and readable figures. The application does not require these document-authoring dependencies.

The checked-in Word, PDF, Markdown, and image files can be read without regenerating them. Guide date: 20 November 2026.
