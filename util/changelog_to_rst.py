"""Parses a SQLAlchemy-style CHANGES file into changelog format.

This is pretty specific to the files changelog was created for.

"""
import sys
import re
import textwrap

# this is a history file generated from "hg log".
# it's parsed for "tag: <sometag>" in order to get the dates
# for releases.   It relates a tag to a release in CHANGELOG
# using the form tag_X_Y_Z -> X.Y.Z.
TAGFILE = "all_my_tags.txt"

def read_dates():
    lines = open(TAGFILE).readlines()
    tags = {}
    for line in lines:
        if line.startswith("changeset:"):
            tag = None
        elif line.startswith("tag:"):
            tag = re.match(r'tag:\s+(.+)', line).group(1)
        elif line.startswith("date:") and tag is not None:
            date, year = re.match(r'date:\s+(\w+ \w+ \d+) \d+:\d+:\d+ (\d+)', line).group(1, 2)

            digits = re.findall(r"(?:^|_)(\d+)", tag)
            extra = re.match(".*?(beta\d|rc\d|[a-z]\d)$", tag)
            if extra:
                extra = extra.group(1)
            else:
                extra = ""

            if len(digits) == 2 and extra:
                versions = ".".join(digits) + extra, \
                            ".".join(digits + ["0"]) + extra
            else:
                versions = (".".join(digits) + extra,)

            for version in versions:
                tags[version] = "%s %s" % (date, year)
    return tags

def raw_blocks(fname):
    lines = open(fname).readlines()

    version_re = re.compile(r'''
                        (
                            ^\d+\.\d+ (?: \.\d+ )?

                            (?:beta\d|rc\d|[a-z]\d?)?
                        )

                        \s*(\(.*\))?$''', re.X)

    bullet_re = re.compile(r'''
          (\s{0,5})-\s(.*)
        ''', re.X)

    normal = 0
    in_bullet = 1
    state = normal

    while lines:
        line = lines.pop(0)
        if state == normal:
            m = version_re.match(line)
            if m:
                yield "version", m.group(1)
                continue

            m = bullet_re.match(line)
            if m:
                state = in_bullet
                bullet_indent = len(m.group(1))
                bullet_lines = [(" " * (bullet_indent + 2)) + m.group(2) + "\n"]
                continue

            yield "ignored", line

        elif state == in_bullet:
            another_bullet = bullet_re.match(line)
            version_number = version_re.match(line)

            if \
                line == "\n" or \
                (
                not another_bullet and not version_number \
                and (
                        (
                            bullet_indent and line.startswith(" " * bullet_indent)
                        ) or not bullet_indent
                    )
                ):
                bullet_lines.append(line)
            else:
                yield "bullet", textwrap.dedent("".join(bullet_lines))

                state = normal
                if another_bullet or version_number:
                    lines.insert(0, line)
                    continue

def tagged(elements):
    current_version = None
    current_tags = set()
    for type_, content in elements:
        if type_ == 'version':
            current_tags = set()
            current_version = content
        elif type_ == 'bullet':
            if len(content.split(' ')) < 3 and "ticket" not in content:
                current_tags = set([re.sub(r'[\s\:]', '', c.lower()) for c in content.split(' ')])
            else:
                in_content_tags = set()
                tickets = set()
                def tag(m):
                    tag_content = m.group(1)
                    t_r = re.match(r'(?:ticket:|#)(\d+)', tag_content)
                    if t_r:
                        tickets.add(t_r.group(1))
                    else:
                        in_content_tags.add(tag_content)

                content = re.sub(r'(?:^|\s)\[(.+?)\]', tag, content)

                content = re.sub(r'\s(#\d+)', tag, content)

                yield {
                    'version': current_version,
                    'tags': ", ".join(current_tags.union(in_content_tags)),
                    'tickets': ", ".join(tickets),
                    'content': content
                }

def emit_rst(records):
    current_version = None
    versions = read_dates()

    current_major_version = None
    current_output_file = None

    for rec in records:
        indented_content = re.compile(r'^', re.M).sub('      ', rec['content'].strip())

        if indented_content.endswith(","):
            indented_content = indented_content[0:-1] + "."

        if rec['version'] != current_version:
            current_version = rec['version']
            released = versions.get(current_version, '')

            major_version = current_version[0:3]
            if major_version != current_major_version:
                if current_output_file:
                    current_output_file.close()
                current_major_version = major_version
                cfile = "changelog_%s.rst" % major_version.replace(".", "")
                print "writing %s" % cfile
                current_output_file = open(cfile, 'w')
                current_output_file.write("""
==============
%s Changelog
==============

                """ % major_version)



            current_output_file.write(
"""
.. changelog::
    :version: %s
    :released: %s
""" % (current_version, released)
)
        current_output_file.write(
"""
    .. change::
        :tags: %s
        :tickets: %s

%s
""" % (
        rec['tags'],
        rec['tickets'],
        indented_content
    )
)


if __name__ == '__main__':
    fname = sys.argv[1]

    emit_rst(tagged(raw_blocks(fname)))