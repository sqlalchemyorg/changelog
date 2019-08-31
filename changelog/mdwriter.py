import io
import sys

from docutils import nodes
from docutils import writers

from .environment import Environment


class Writer(writers.Writer):

    supported = ("markdown",)

    def translate(self):
        translator = MarkdownTranslator(self.document)
        self.document.walkabout(translator)
        self.output = translator.buf.getvalue()


class MarkdownTranslator(nodes.NodeVisitor):
    def __init__(self, document):
        super(MarkdownTranslator, self).__init__(document)
        self.buf = io.StringIO()
        self.section = 0
        self.stack = []

    def visit_document(self, node):
        self.document = node
        self.env = Environment.from_document_settings(self.document.settings)

    def visit_section(self, node):
        self.section += 1

    def depart_section(self, node):
        self.section -= 1

    def visit_strong(self, node):
        self.buf.write("**")

    def depart_strong(self, node):
        self.buf.write("**")

    def visit_emphasis(self, node):
        self.buf.write("*")

    def depart_emphasis(self, node):
        self.buf.write("*")

    def visit_literal(self, node):
        self.buf.write("`")

    def visit_Text(self, node):
        self.buf.write(node.astext())

    def depart_Text(self, node):
        pass

    def depart_paragraph(self, node):
        self.buf.write("\n\n")

    def depart_literal(self, node):
        self.buf.write("`")

    def visit_title(self, node):
        if "version_string" in node.attributes:
            pass
        self.buf.write("\n%s %s\n\n" % ("#" * self.section, node.astext()))
        raise nodes.SkipNode()

    def visit_changeset_link(self, node):
        # it would be nice to have an absolutely link to the HTML
        # hosted changelog but this requires being able to generate
        # the absolute link from the document filename and all that.
        # it can perhaps be sent on the commandline
        raise nodes.SkipNode()

    def depart_changeset_link(self, node):
        pass

    def visit_reference(self, node):
        if "changelog-reference" in node.attributes["classes"]:
            self.visit_changeset_link(node)
        else:
            self.buf.write("[")

    def depart_reference(self, node):
        if "changelog-reference" in node.attributes["classes"]:
            self.depart_changeset_link(node)
        else:
            self.buf.write("](%s)" % node.attributes["refuri"])

    def visit_admonition(self, node):
        # "seealsos" typically have internal sphinx references so at the
        # moment we're not prepared to look those up, future version can
        # perhaps use sphinx object lookup
        raise nodes.SkipNode()

    def visit_list_item(self, node):
        self.stack.append(self.buf)
        self.buf = io.StringIO()

    def depart_list_item(self, node):
        popped = self.buf
        self.buf = self.stack.pop(-1)

        indent_level = len(self.stack)
        indent_string = " " * 4 * indent_level

        value = popped.getvalue().strip()

        lines = value.split("\n")
        self.buf.write(indent_string + "-   ")
        line = lines.pop(0)
        self.buf.write(line + "\n")
        for line in lines:
            self.buf.write(indent_string + "    " + line + "\n")

    def _visit_generic_node(self, nodename):
        sys.stderr.write("generic node: %s\n" % nodename)

        def go(node):
            pass

        return go

    def __getattr__(self, name):
        if not name.startswith("_"):
            return self._visit_generic_node(name)
        else:
            raise AttributeError(name)
