import argparse
import os
import re
import shutil
import sys
import tempfile

from . import mdwriter


def release_notes_into_changelog_file(target_filename, version, release_date):
    """Read changelog fragment files and render them into a single .rst file.

    remove the fragment files afterwards using git rm.

    The fragment files are located by looking for ':include_notes_from:'
    directives in the given changelog file.

    """
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
    subparser.add_argument(
        "-v",
        "--version",
        type=str,
        help="render changelog only for version given",
    )
    subparser.add_argument(
        "-s",
        "--sections-only",
        action="store_true",
        help="render changelogs as top level sections",
    )
    subparser.set_defaults(
        cmd=(
            mdwriter.render_changelog_as_md,
            ["filename", "config", "version", "sections_only"],
        )
    )

    options = parser.parse_args(argv)
    fn, argnames = options.cmd
    fn(*[getattr(options, name) for name in argnames])


if __name__ == "__main__":
    main(sys.argv)
