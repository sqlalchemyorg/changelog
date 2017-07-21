import re
from docutils.parsers.rst import Directive
from docutils import nodes
from sphinx.util.console import bold
import os
from sphinx.util.osutil import copyfile
from . import render
import copy


def _is_html(app):
    return app.builder.name in ('html', 'readthedocs')


def _comma_list(text):
    return re.split(r"\s*,\s*", text.strip())


def _parse_content(content):
    d = {}
    d['text'] = []
    idx = 0
    for line in content:
        idx += 1
        m = re.match(r' *\:(.+?)\:(?: +(.+))?', line)
        if m:
            attrname, value = m.group(1, 2)
            d[attrname] = value or ''
        elif idx == 1 and line:
            # accomodate a unique value on the edge of .. change::
            continue
        else:
            break
    d["text"] = content[idx:]
    return d


class EnvDirective(object):
    @property
    def env(self):
        return self.state.document.settings.env

    @classmethod
    def get_changes_list(cls, env):
        if 'ChangeLogDirective_changes' not in env.temp_data:
            env.temp_data['ChangeLogDirective_changes'] = []
        return env.temp_data['ChangeLogDirective_changes']


class ChangeLogDirective(EnvDirective, Directive):
    """Implement the ``.. changelog::`` directive.

    """
    has_content = True

    default_section = 'misc'

    def run(self):
        self._parse()

        if not ChangeLogImportDirective.in_include_directive(self.env):
            return render.render_changelog(self)
        else:
            return []

    def _parse(self):
        # 1. pull in global configuration from conf.py
        self.sections = self.env.config.changelog_sections
        self.inner_tag_sort = self.env.config.changelog_inner_tag_sort + [""]

        # 2. examine top level directives inside the .. changelog::
        # directive.  version, release date
        self._parsed_content = parsed = _parse_content(self.content)
        self.version = version = parsed.get('version', '')
        self.release_date = parsed.get('released', None)
        self.is_released = bool(self.release_date)
        self.env.temp_data['ChangeLogDirective_version'] = version

        content = self.content

        # 3. read extra per-file included notes
        if 'include_notes_from' in parsed:
            if content.items and content.items[0]:
                source = content.items[0][0]
                path = os.path.join(
                    os.path.dirname(source), parsed['include_notes_from'])
            else:
                path = parsed['include_notes_from']
            if not os.path.exists(path):
                raise Exception("included nodes path %s does not exist" % path)

            content = copy.deepcopy(content)
            for fname in os.listdir(path):
                fpath = os.path.join(path, fname)
                print "READING!!! %s %s %s" % (version, self, fpath)
                with open(fpath) as handle:
                    content.append("", path, 0)
                    for num, line in enumerate(handle):
                            line = line.rstrip()
                            content.append(
                                line, path, num
                            )

        # 4. parse the content of the .. changelog:: directive. This
        # is where we parse individual .. change:: directives and construct
        # a list of items, stored in the env via self.get_changes_list(env)
        p = nodes.paragraph('', '',)
        self.state.nested_parse(content[1:], 0, p)


class ChangeLogImportDirective(EnvDirective, Directive):
    """Implement the ``.. changelog_imports::`` directive.

    Here, we typically load in other changelog.rst files which may feature
    elements that also apply to our current changelog.rst file, when they
    specify the ``:version:`` modifier.

    """
    has_content = True

    @classmethod
    def in_include_directive(cls, env):
        return 'ChangeLogDirective_includes' in env.temp_data

    def run(self):
        # tell ChangeLogDirective we're here, also prevent
        # nested .. include calls
        if not self.in_include_directive(self.env):
            self.env.temp_data['ChangeLogDirective_includes'] = True
            p = nodes.paragraph('', '',)
            self.state.nested_parse(self.content, 0, p)
            del self.env.temp_data['ChangeLogDirective_includes']

        return []


class ChangeDirective(EnvDirective, Directive):
    """Implement the ``.. change::`` directive.

    """
    has_content = True

    def run(self):
        # don't do anything if we're not inside of a version
        if 'ChangeLogDirective_version' not in self.env.temp_data:
            return []

        content = _parse_content(self.content)
        p = nodes.paragraph('', '',)
        sorted_tags = _comma_list(content.get('tags', ''))
        declared_version = self.env.temp_data['ChangeLogDirective_version']
        versions = set(
            _comma_list(content.get("versions", ""))).difference(['']).\
            union([declared_version])

        # if we don't refer to any other versions and we're in an include,
        # skip
        if len(versions) == 1 and \
                ChangeLogImportDirective.in_include_directive(self.env):

            return []

        def int_ver(ver):
            out = []
            for dig in ver.split("."):
                try:
                    out.append(int(dig))
                except ValueError:
                    out.append(0)
            return tuple(out)

        rec = {
            'tags': set(sorted_tags).difference(['']),
            'tickets': set(
                _comma_list(content.get('tickets', ''))).difference(['']),
            'pullreq': set(
                _comma_list(content.get('pullreq', ''))).difference(['']),
            'changeset': set(
                _comma_list(content.get('changeset', ''))).difference(['']),
            'node': p,
            'type': "change",
            "title": content.get("title", None),
            'sorted_tags': sorted_tags,
            "versions": versions,
            "sorted_versions": list(reversed(sorted(versions, key=int_ver)))
        }

        self.state.nested_parse(content['text'], 0, p)
        ChangeLogDirective.get_changes_list(self.env).append(rec)

        return []


def make_ticket_link(
        name, rawtext, text, lineno, inliner,
        options={}, content=[]):
    env = inliner.document.settings.env
    render_ticket = env.config.changelog_render_ticket or "%s"
    prefix = "#%s"
    if render_ticket:
        ref = render_ticket % text
        node = nodes.reference(rawtext, prefix % text, refuri=ref, **options)
    else:
        node = nodes.Text(prefix % text, prefix % text)
    return [node], []


def add_stylesheet(app):
    app.add_stylesheet('changelog.css')


def copy_stylesheet(app, exception):
    app.info(
        bold('The name of the builder is: %s' % app.builder.name), nonl=True)

    if not _is_html(app) or exception:
        return
    app.info(bold('Copying sphinx_paramlinks stylesheet... '), nonl=True)

    source = os.path.abspath(os.path.dirname(__file__))

    # the '_static' directory name is hardcoded in
    # sphinx.builders.html.StandaloneHTMLBuilder.copy_static_files.
    # would be nice if Sphinx could improve the API here so that we just
    # give it the path to a .css file and it does the right thing.
    dest = os.path.join(app.builder.outdir, '_static', 'changelog.css')
    copyfile(os.path.join(source, "changelog.css"), dest)
    app.info('done')


def setup(app):
    app.add_directive('changelog', ChangeLogDirective)
    app.add_directive('change', ChangeDirective)
    app.add_directive('changelog_imports', ChangeLogImportDirective)
    app.add_config_value("changelog_sections", [], 'env')
    app.add_config_value("changelog_inner_tag_sort", [], 'env')
    app.add_config_value("changelog_render_ticket", None, 'env')
    app.add_config_value("changelog_render_pullreq", None, 'env')
    app.add_config_value("changelog_render_changeset", None, 'env')
    app.connect('builder-inited', add_stylesheet)
    app.connect('build-finished', copy_stylesheet)
    app.add_role('ticket', make_ticket_link)
