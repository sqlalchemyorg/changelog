from docutils.parsers.rst import directives

from .sphinxext import ChangeDirective
from .sphinxext import ChangeLogDirective
from .sphinxext import ChangeLogImportDirective


def setup_docutils():
    directives.register_directive("changelog", ChangeLogDirective)
    directives.register_directive("change", ChangeDirective)
    directives.register_directive(
        "changelog_imports", ChangeLogImportDirective
    )
