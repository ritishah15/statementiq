# StatementIQ Documentation

Ready-to-share deliverables generated from the running application and source code.

| File | Pages | Format | Description |
|---|---:|---|---|
| [`StatementIQ_Architecture_Documentation.pdf`](StatementIQ_Architecture_Documentation.pdf) | 20 | A4 portrait | Full architecture and technical documentation: context, containers, six-stage pipeline, OCR routing, parsing/validation, classification, data model, API, deployment, security, UI walkthrough, model evaluation, testing and roadmap. |
| [`StatementIQ_Architecture_Diagrams.pdf`](StatementIQ_Architecture_Diagrams.pdf) | 8 | A4 landscape | Standalone diagram pack for presentations and review: context, container view, pipeline, OCR routing, parsing/validation, classification, data model and deployment. |

## Source files

- `architecture.html` — source of the 20-page document (inline SVG diagrams + UI captures).
- `diagram_pack.html` — source of the landscape diagram pack.
- `assets/` — screenshots captured from the live UI.

## Regenerating

```bash
# from the project root
python scratch/print_pdf.py
python scratch/build_diagram_pack.py
python scratch/print_pack.py
```

The screenshots were captured with headless Chrome from `http://localhost:5173` using a processed scanned statement (`STMT-5BAC4B30`, 17 transactions).
