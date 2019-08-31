import argparse
import os
import re
import shutil
import sys
import tempfile

from docutils.core import publish_file

from . import docutils
from .docutils import Environment


def release_notes_into_changelog_file(target_filename, version, release_date):
    output = tempfile.NamedTemporaryFile(
        mode="w", delete=False, encoding="utf-8"
    )
    with open(target_filename) as handle:
        for line in handle:
            m = re.match(r".*:version: %s" % version, line)
            if m:
                output.write(line)
                output.write("    :released: %s\n" % release_date)
                continue

            m = re.match(r".*:include_notes_from: (.+)", line)
            if m:
                notes_dir = os.path.join(
                    os.path.dirname(target_filename), m.group(1)
                )
                for fname in os.listdir(notes_dir):
                    if not fname.endswith(".rst"):
                        continue
                    fname_path = os.path.join(notes_dir, fname)
                    output.write("\n")
                    with open(fname_path) as inner:
                        for inner_line in inner:
                            output.write(("    " + inner_line).rstrip() + "\n")
                    os.system("git rm %s" % fname_path)
            else:
                output.write(line)
    output.close()
    shutil.move(output.name, target_filename)


class CmdEnvironment(Environment):
    def __init__(self, config):
        self._temp_data = {}
        self.config = config

    @property
    def temp_data(self):
        return self._temp_data

    @property
    def changelog_sections(self):
        return self.config.get("changelog_sections", [])

    @property
    def changelog_inner_tag_sort(self):
        return self.config.get("inner_tag_sort", [])

    @property
    def changelog_render_ticket(self):
        return self.config.get("changelog_render_ticket", "ticket:%s")

    @property
    def changelog_render_pullreq(self):
        return self.config.get("changelog_render_pullreq", "pullreq:%s")

    @property
    def changelog_render_changeset(self):
        return self.config.get("changelog_render_changeset", "changeset:%s")

    def status_iterator(self, elements, message):
        for element in elements:
            print(message)
            yield element


def render_changelog_as_md(target_filename, config_filename):
    locals_ = {}
    if config_filename is not None:
        exec(open(config_filename).read(), locals_)
    docutils.setup_docutils()
    with open(target_filename) as handle:
        print(
            publish_file(
                handle,
                settings_overrides={"changelog_cmd": CmdEnvironment(locals_)},
            )
        )


def main(argv=None):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    subparser = subparsers.add_parser(
        "release-notes", help="Merge notes files into changelog and git rm"
    )
    subparser.add_argument("filename", help="target changelog filename")
    subparser.add_argument(
        "version", help="version string as it appears in changelog"
    )
    subparser.add_argument("date", help="full text of datestamp to insert")
    subparser.set_defaults(
        cmd=(
            release_notes_into_changelog_file,
            ["filename", "version", "date"],
        )
    )

    subparser = subparsers.add_parser(
        "generate-md", help="Generate file into markdown"
    )
    subparser.add_argument("filename", help="target changelog filename")
    subparser.add_argument("-c", "--config", help="path to conf.py")
    subparser.set_defaults(
        cmd=(render_changelog_as_md, ["filename", "config"])
    )

    options = parser.parse_args(argv)
    fn, argnames = options.cmd
    fn(*[getattr(options, name) for name in argnames])


if __name__ == "__main__":
    main(sys.argv)
