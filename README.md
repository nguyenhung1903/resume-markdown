# BUILD RESUME
build.py - Markdown CV  ->  resume (HTML + PDF)

Reads a Markdown CV, converts it to structured HTML, applies
`css/academic_resume.css`, and writes BOTH:
    <out>/<name>.html   (self-contained, CSS embedded)
    <out>/<name>.pdf    (A4, generated with WeasyPrint)

Usage:
    python build.py
    python build.py -i CV_NguyenAnHung.md -c academic_resume.css \
                           -o dist -n resume

Install:
    pip install markdown weasyprint

Expected Markdown shape (same as CV_NguyenAnHung.md):
    # Name
    **TITLE**
    Location
    - contact items...
    ## Section
    ### Organisation / Title
    *Location*
    **Role** - period
    - bullets