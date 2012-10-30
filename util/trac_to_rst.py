"""Parses a trac wiki page into rst."""

import sys
import re
import textwrap


def structure(fname):
    lines = open(fname).readlines()

    plain = 0
    bullet = 1
    state = plain

    current_chunk = []
    current_indent = ""

    while lines:
        line = lines.pop(0).rstrip()

        line_indent = re.match(r'^(\s*)', line)
        line_indent = len(line_indent.group(1))

        bullet_m = re.match(r'^(\s*)\* (.*)', line)
        if bullet_m:
            if current_chunk:
                yield {
                    "bullet": state == bullet,
                    "indent": len(current_indent) if state == bullet else 0,
                    "lines": current_chunk
                }
            current_chunk = []

            current_indent = bullet_m.group(1)
            line = bullet_m.group(2)
            state = bullet
            current_chunk.append(line)
        elif state == bullet:
            if not line:
                current_chunk.append(line)
            elif (
                line
                and (
                        # line indent is less
                        line_indent < len(current_indent)
                        or

                        # or no indent and previous line was blank
                        (not line_indent and len(current_indent) == 0 and current_chunk and not current_chunk[-1])
                    )
                ):
                yield {
                    "bullet": True,
                    "indent": len(current_indent),
                    "lines": current_chunk
                }
                current_chunk = []
                state = plain
                current_chunk.append(line)
            else:
                current_chunk.append(line[len(current_indent):])
        #elif not line:
        #    if current_chunk:
        #        yield {
        #            "bullet": state == bullet,
        #           "indent": len(current_indent) if state == bullet else 0,
        #            "lines": current_chunk
        #        }
        #       current_chunk = []
        else:
            current_chunk.append(line)

    yield {
        "bullet": state == bullet,
        "indent": len(current_indent) if state == bullet else 0,
        "lines": current_chunk
    }

def bullet_depth(recs):
    bullet_indent = 0
    rec_indent = 0
    for rec in recs:

        if rec['bullet']:
            if bullet_indent:
                if rec['indent'] > rec_indent:
                    bullet_indent += 1
                elif rec['indent'] < rec_indent:
                    bullet_indent -= 1
            else:
                bullet_indent = 1
        else:
            bullet_indent = 0

        rec_indent = rec['indent']

        rec['bullet_depth'] = bullet_indent
        yield rec

def code(recs):
    for rec in recs:
        code = False
        current_chunk = []

        asterisk = rec['bullet']

        for line in rec["lines"]:

            if re.match(r'^\s*{{{', line):
                code = True

                if current_chunk:
                    yield {
                        'bullet_depth': rec['bullet_depth'],
                        'lines': current_chunk,
                        'code': False,
                        'asterisk': asterisk
                    }
                    asterisk = False
                    current_chunk = []


            elif re.match(r'^\s*}}}', line):
                code = False
                if current_chunk:
                    yield {
                        'bullet_depth': rec['bullet_depth'],
                        'lines': current_chunk,
                        'code': True
                    }
                    current_chunk = []

            elif code:
                if not re.match(r'^\s*#!', line):
                    current_chunk.append(line)
            elif not line:
                if current_chunk:
                    yield {
                        'bullet_depth': rec['bullet_depth'],
                        'lines': current_chunk,
                        'code': False,
                        'asterisk': asterisk
                    }
                asterisk = False
                current_chunk = []
            else:
                if line == "----" or \
                    line.startswith("[[PageOutline"):
                    continue
                line = re.sub(r'(\*\*?\w+)(?!\*)\b', lambda m: "\\%s" % m.group(1), line)
                line = re.sub(r'\!(\w+)\b', lambda m: m.group(1), line)
                line = re.sub(r"`(.+?)`", lambda m: "``%s``" % m.group(1), line)
                line = re.sub(r"'''(.+?)'''", lambda m: "**%s**" % m.group(1).replace("``", ""), line)
                line = re.sub(r"''(.+?)'", lambda m: "*%s*" % m.group(1).replace("``", ""), line)
                line = re.sub(r'\[(http://\S+) (.*)\]',
                        lambda m: "`%s <%s>`_" % (m.group(2), m.group(1)),
                        line
                    )
                line = re.sub(r'#(\d+)', lambda m: ":ticket:`%s`" % m.group(1), line)

                if line.startswith("=") and line.endswith("="):
                    if current_chunk:
                        yield {
                            'bullet_depth': rec['bullet_depth'],
                            'lines': current_chunk,
                            'code': False,
                            'asterisk': asterisk,
                        }
                        asterisk = False
                        current_chunk = []

                    header_lines = output_header(line)
                    yield {
                        'bullet_depth': 0,
                        'lines': header_lines,
                        'code': False,
                        'asterisk': False,
                        'header': True
                    }
                else:
                    if line or current_chunk:
                        current_chunk.append(line)

        if current_chunk:
            yield {
                'bullet_depth': rec['bullet_depth'],
                'lines': current_chunk,
                'code': False,
                'asterisk': asterisk
            }


def render(recs):
    for rec in recs:
        bullet_depth = rec['bullet_depth']

        bullet_indent = "  " * bullet_depth

        if rec.get('header', False):
            print "\n".join(rec['lines'])
            print ""
        elif rec['code']:
            text = "\n".join(
                bullet_indent + "    " + line
                for line in rec['lines']
            )
            print bullet_indent + "::\n"
            print text

            print ""
        else:
            text = textwrap.dedent("\n".join(rec['lines']))
            lines = textwrap.wrap(text, 60 - (2 * bullet_depth))

            if rec['asterisk']:
                line = lines.pop(0)
                print ("  " * (bullet_depth - 1)) + "* " + line

            print "\n".join(
                    [bullet_indent + line for line in lines]
                    )

            print ""

def remove_double_blanks(lines):
    blank = 0
    for line in lines:
        for subline in line.split("\n"):
            if not subline:
                blank += 1
            else:
                blank = 0
            if blank < 2:
                yield subline

def output_header(line):
    line = line.strip()
    m = re.match(r'^(=+) (.*?) =+$', line)
    depth = len(m.group(1))
    if depth == 1:
        return [
                    "=" * len(m.group(2)),
                    m.group(2),
                    "=" * len(m.group(2))
                ]
    char = {
        2: "=",
        3: "-",
        4: "^"
    }[depth]
    return [
                m.group(2),
                char * len(m.group(2))
            ]

if __name__ == '__main__':
    fname = sys.argv[1]

#    for rec in structure(fname):
#        print rec
    render(code(bullet_depth(structure(fname))))
