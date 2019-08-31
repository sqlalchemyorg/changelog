import os

from sphinx.util import logging
from sphinx.util import status_iterator
from sphinx.util.console import bold
from sphinx.util.osutil import copyfile

from .docutils import ChangeDirective
from .docutils import ChangeLogDirective
from .docutils import ChangeLogImportDirective
from .docutils import Environment
from .docutils import make_ticket_link


LOG = logging.getLogger(__name__)


def _is_html(app):
    return app.builder.name in ("html", "readthedocs")


class SphinxEnvironment(Environment):
    __slots__ = ("sphinx_env",)

    def __init__(self, sphinx_env):
        self.sphinx_env = sphinx_env

    @property
    def temp_data(self):
        return self.sphinx_env.temp_data

    @property
    def changelog_sections(self):
        return self.sphinx_env.config.changelog_sections

    @property
    def changelog_inner_tag_sort(self):
        return self.sphinx_env.config.changelog_inner_tag_sort

    @property
    def changelog_render_ticket(self):
        return self.sphinx_env.config.changelog_render_ticket

    @property
    def changelog_render_pullreq(self):
        return self.sphinx_env.config.changelog_render_pullreq

    @property
    def changelog_render_changeset(self):
        return self.sphinx_env.config.changelog_render_changeset

    def status_iterator(self, elements, message):
        return status_iterator(
            elements,
            message,
            "purple",
            length=len(elements),
            verbosity=self.sphinx_env.app.verbosity,
        )


def add_stylesheet(app):
    app.add_stylesheet("changelog.css")


def copy_stylesheet(app, exception):
    LOG.info(
        bold("The name of the builder is: %s" % app.builder.name), nonl=True
    )

    if not _is_html(app) or exception:
        return
    LOG.info(bold("Copying sphinx_paramlinks stylesheet... "), nonl=True)

    source = os.path.abspath(os.path.dirname(__file__))

    # the '_static' directory name is hardcoded in
    # sphinx.builders.html.StandaloneHTMLBuilder.copy_static_files.
    # would be nice if Sphinx could improve the API here so that we just
    # give it the path to a .css file and it does the right thing.
    dest = os.path.join(app.builder.outdir, "_static", "changelog.css")
    copyfile(os.path.join(source, "changelog.css"), dest)
    LOG.info("done")


def setup(app):
    app.add_directive("changelog", ChangeLogDirective)
    app.add_directive("change", ChangeDirective)
    app.add_directive("changelog_imports", ChangeLogImportDirective)
    app.add_config_value("changelog_sections", [], "env")
    app.add_config_value("changelog_inner_tag_sort", [], "env")
    app.add_config_value("changelog_render_ticket", None, "env")
    app.add_config_value("changelog_render_pullreq", None, "env")
    app.add_config_value("changelog_render_changeset", None, "env")
    app.connect("builder-inited", add_stylesheet)
    app.connect("build-finished", copy_stylesheet)
    app.add_role("ticket", make_ticket_link)
