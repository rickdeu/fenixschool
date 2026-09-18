# Kiaalap — Third-Party Assets

The CSS/JS/font files in this directory (`main.css`, `dashboard.css`,
`main.js`, `bootstrap-icons-*.woff*`, `logo.png`) are compiled output from
the **Kiaalap** education admin dashboard template, extracted for issue
#187 (adopting a modern visual base for `admin_panel`).

- **Source**: https://github.com/puikinsh/kiaalap
- **Author**: [Colorlib](https://colorlib.com/)
- **License**: MIT

Per the MIT License, Colorlib must be credited as the original author of
this template wherever it is used — see the `credit-colorlib` footer note
rendered by `templates/base.html`.

Only the compiled core assets actually used by FenixSchool's own pages were
kept (Bootstrap 5 + the base dashboard layout/theme). The template's many
demo-only libraries (charts, maps, a rich-text editor, a PDF viewer, a code
editor, etc.) were intentionally left out, since nothing in this project
uses them yet — add them the same way, from the same source, if a real
feature ever needs one.
