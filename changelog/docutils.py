import collections
import hashlib as md5
import os
import re
import sys
import warnings

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives
from docutils.parsers.rst import roles
from looseversion import LooseVersion

from . import generate_rst
from .environment import Environment

py3k = sys.version_info >= (3, 0)


def _comma_list(text):
    return re.split(r"\s*,\s*", text.strip())


def _parse_content(content):
    d = {}
    d["text"] = []
    idx = 0
    for line in content:
        idx += 1
        m = re.match(r" *\:(.+?)\:(?: +(.+))?", line)
        if m:
            attrname, value = m.group(1, 2)
            d[attrname] = value or ""
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
        return Environment.from_document_settings(self.state.document.settings)

    @classmethod
    def get_changes_list(cls, env, hash_on_version):
        key = ("ChangeLogDirective_changes", hash_on_version)
        if key not in env.temp_data:
            env.temp_data[key] = collections.OrderedDict()
        return env.temp_data[key]


class ChangeLogDirective(EnvDirective, Directive):
    """Implement the ``.. changelog::`` directive."""

    has_content = True

    default_section = "misc"

    def run(self):
        self._parse()

        if not ChangeLogImportDirective.in_include_directive(self.env):
            return generate_rst.render_changelog(self)
        else:
            return []

    def _parse(self):
        # 1. pull in global configuration from conf.py
        self.sections = self.env.changelog_sections
        self.caption_classes = self.env.changelog_caption_class.split(" ")
        self.inner_tag_sort = self.env.changelog_inner_tag_sort + [""]
        self.hide_sections_from_tags = bool(
            self.env.changelog_hide_sections_from_tags
        )
        self.hide_tags_in_entry = bool(self.env.changelog_hide_tags_in_entry)

        # 2. examine top level directives inside the .. changelog::
        # directive.  version, release date
        self._parsed_content = parsed = _parse_content(self.content)
        self.version = version = parsed.get("version", "")
        self.release_date = parsed.get("released", None)
        self.is_released = bool(self.release_date)
        self.env.temp_data["ChangeLogDirective"] = self

        content = self.content

        # 3. read extra per-file included notes
        if "include_notes_from" in parsed:
            if content.items and content.items[0]:
                source = content.items[0][0]

                # seems we are now getting strings like:
                # changelog/changelog_11.rst <included from
                # /home/classic/dev/sqlalchemy/doc/build/changelog/changelog_12.rst>
                source = source.split(" ")[0]

                path = os.path.join(
                    os.path.dirname(source), parsed["include_notes_from"]
                )
            else:
                path = parsed["include_notes_from"]
            if not os.path.exists(path):
                raise Exception("included nodes path %s does not exist" % path)

            files = [
                fname for fname in os.listdir(path) if fname.endswith(".rst")
            ]
            for fname in self.env.status_iterator(
                files, "reading changelog note files (version %s)..." % version
            ):
                fpath = os.path.join(path, fname)
                self.env.sphinx_env.note_dependency(fpath)
                with open(fpath) as handle:
                    content.append("", path, 0)
                    for num, line in enumerate(handle):
                        if not py3k:
                            line = line.decode("utf-8")
                        if "\t" in line:
                            warnings.warn(
                                "file %s has a tab in it! please "
                                "convert to spaces." % fname
                            )
                            line = line.replace("\t", "    ")
                        line = line.rstrip()
                        content.append(line, path, num)

        # 4. parse the content of the .. changelog:: directive. This
        # is where we parse individual .. change:: directives and construct
        # a list of items, stored in the env via self.get_changes_list(env)
        p = nodes.paragraph("", "")
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
        return "ChangeLogDirective_includes" in env.temp_data

    def run(self):
        # tell ChangeLogDirective we're here, also prevent
        # nested .. include calls
        if not self.in_include_directive(self.env):
            self.env.temp_data["ChangeLogDirective_includes"] = True
            p = nodes.paragraph("", "")
            self.state.nested_parse(self.content, 0, p)
            del self.env.temp_data["ChangeLogDirective_includes"]
        return []


class SeeAlsoDirective(EnvDirective, Directive):
    """implement a quick version of Sphinx "seealso" when running outside
    of sphinx."""

    has_content = True

    def run(self):
        text = "\n".join(self.content)
        ad = nodes.admonition(rawsource=text)
        st = nodes.strong()
        st.append(nodes.Text("See also:"))
        ad.append(st)
        ad.append(nodes.Text("\n"))
        self.state.nested_parse(self.content, 0, ad)
        return [ad]


class ChangeDirective(EnvDirective, Directive):
    """Implement the ``.. change::`` directive."""

    has_content = True

    def run(self):
        # don't do anything if we're not inside of a version
        if "ChangeLogDirective" not in self.env.temp_data:
            return []

        content = _parse_content(self.content)

        sorted_tags = _comma_list(content.get("tags", ""))
        changelog_directive = self.env.temp_data["ChangeLogDirective"]
        declared_version = changelog_directive.version
        versions = (
            set(_comma_list(content.get("versions", "")))
            .difference([""])
            .union([declared_version])
        )

        # if we don't refer to any other versions and we're in an include,
        # skip
        if len(
            versions
        ) == 1 and ChangeLogImportDirective.in_include_directive(self.env):

            return []

        body_paragraph = nodes.paragraph(
            "", "", classes=changelog_directive.caption_classes
        )
        self.state.nested_parse(content["text"], 0, body_paragraph)

        raw_text = _text_rawsource_from_node(body_paragraph)
        tickets = set(_comma_list(content.get("tickets", ""))).difference([""])
        pullreq = set(_comma_list(content.get("pullreq", ""))).difference([""])
        tags = set(sorted_tags).difference([""])

        for hash_on_version in versions:
            issue_hash = _get_robust_version_hash(
                raw_text, hash_on_version, tickets, tags
            )

            rec = ChangeLogDirective.get_changes_list(
                changelog_directive.env, hash_on_version
            ).setdefault(issue_hash, {})
            if not rec:
                sorted(versions, key=_str_version_as_tuple)
                rec.update(
                    {
                        "hash": issue_hash,
                        "render_for_version": hash_on_version,
                        "tags": tags,
                        "tickets": tickets,
                        "pullreq": pullreq,
                        "changeset": set(
                            _comma_list(content.get("changeset", ""))
                        ).difference([""]),
                        "node": body_paragraph,
                        "raw_text": raw_text,
                        "type": "change",
                        "title": content.get("title", None),
                        "sorted_tags": sorted_tags,
                        "versions": versions,
                        "version_to_hash": {
                            version: _get_legacy_version_hash(
                                raw_text, version
                            )
                            for version in versions
                        },
                        "source_versions": [declared_version],
                        "sorted_versions": list(
                            reversed(
                                sorted(versions, key=_str_version_as_tuple)
                            )
                        ),
                    }
                )
            else:
                # This seems to occur repeated times for each included
                # changelog, not clear if sphinx has changed the scope
                # of self.env to lead to this occurring more often
                self.env.log_debug(
                    "Merging changelog record '%s' from version(s) %s "
                    "with that of version %s",
                    _quick_rec_str(rec),
                    ", ".join(rec["source_versions"]),
                    declared_version,
                )
                rec["source_versions"].append(declared_version)

                assert rec["raw_text"] == raw_text
                assert rec["tags"] == tags
                assert rec["render_for_version"] == hash_on_version

                rec["tickets"].update(tickets)
                rec["pullreq"].update(pullreq)
                rec["changeset"].update(
                    set(_comma_list(content.get("changeset", ""))).difference(
                        [""]
                    )
                )
                rec["versions"].update(versions)

                rec["version_to_hash"].update(
                    {
                        version: _get_legacy_version_hash(raw_text, version)
                        for version in versions
                    }
                )
                rec["sorted_versions"] = list(
                    reversed(
                        sorted(rec["versions"], key=_str_version_as_tuple)
                    )
                )

        return []


def _quick_rec_str(rec):
    """try to print an identifiable description of a record"""

    if rec["tickets"]:
        return "[tickets: %s]" % ", ".join(rec["tickets"])
    else:
        return "%s..." % rec["raw_text"][0:25]


def _get_legacy_version_hash(raw_text, version):
    # this needs to stay like this for link compatibility
    # with thousands of already-published changelogs
    to_hash = "%s %s" % (version, raw_text[0:100])
    return md5.md5(to_hash.encode("ascii", "ignore")).hexdigest()


def _get_robust_version_hash(raw_text, version, tickets, tags):
    # this needs to stay like this for link compatibility
    # with thousands of already-published changelogs
    to_hash = "%s %s %s %s" % (
        version,
        ", ".join(tickets),
        ", ".join(tags),
        raw_text,
    )
    return md5.md5(to_hash.encode("ascii", "ignore")).hexdigest()


def _text_rawsource_from_node(node):
    src = []
    stack = [node]
    while stack:
        n = stack.pop(0)
        if isinstance(n, nodes.Text):
            src.append(str(n))
        stack.extend(n.children)
    return "".join(src)


_VERSION_IDS = {}


def _str_version_as_tuple(ver):
    if ver in _VERSION_IDS:
        return _VERSION_IDS[ver]

    result = LooseVersion(ver)
    _VERSION_IDS[ver] = result
    return result


def make_ticket_link(
    name, rawtext, text, lineno, inliner, options={}, content=[]
):
    env = Environment.from_document_settings(inliner.document.settings)

    render_ticket = env.changelog_render_ticket or "%s"
    prefix = "#%s"
    if render_ticket:
        ref = render_ticket % text
        node = nodes.reference(rawtext, prefix % text, refuri=ref, **options)
    else:
        node = nodes.Text(prefix % text, prefix % text)
    return [node], []


def make_generic_attrref(
    name, rawtext, text, lineno, inliner, options={}, content=[]
):
    text = text.lstrip(".")
    lt = nodes.literal(rawtext=rawtext)
    lt.append(nodes.Text(text))
    return [lt], []


def make_generic_funcref(
    name, rawtext, text, lineno, inliner, options={}, content=[]
):
    if not text.endswith("()"):
        text += "()"
    return make_generic_attrref(
        name, rawtext, text, lineno, inliner, options, content
    )


def make_generic_docref(
    name, rawtext, text, lineno, inliner, options={}, content=[]
):
    lt = nodes.literal(rawtext=rawtext)
    lt.append(nodes.Text(text))
    return [lt], []


def setup_docutils():
    """register docutils directives and roles assuming Sphinx is not in use."""

    directives.register_directive("changelog", ChangeLogDirective)
    directives.register_directive("change", ChangeDirective)
    directives.register_directive(
        "changelog_imports", ChangeLogImportDirective
    )
    directives.register_directive("seealso", SeeAlsoDirective)
    roles.register_canonical_role("ticket", make_ticket_link)

    # sphinx autodoc stuff we don't have in this context
    roles.register_canonical_role("func", make_generic_funcref)
    roles.register_canonical_role("class", make_generic_attrref)
    roles.register_canonical_role("paramref", make_generic_attrref)
    roles.register_canonical_role("attr", make_generic_attrref)
    roles.register_canonical_role("mod", make_generic_attrref)
    roles.register_canonical_role("meth", make_generic_funcref)
    roles.register_canonical_role("obj", make_generic_attrref)
    roles.register_canonical_role("exc", make_generic_attrref)

    roles.register_canonical_role("doc", make_generic_docref)
    roles.register_canonical_role("ref", make_generic_docref)
