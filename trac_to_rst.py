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
                    "indent": len(current_indent),
                    "lines": current_chunk
                }
            current_chunk = []

            current_indent = bullet_m.group(1)
            line = bullet_m.group(2)
            state = bullet
            current_chunk.append(line)
        elif state == bullet:

            # in bullet with no indent, and a blank
            # line - bullet ends
            if (not line and not current_indent and line_indent == 0) or \
                (line and line_indent < len(current_indent)
                ):
                yield {
                    "bullet": True,
                    "indent": len(current_indent),
                    "lines": current_chunk
                }
                current_chunk = []
                state = plain
            else:
                current_chunk.append(line[len(current_indent):])
        elif not line:
            if current_chunk:
                yield {
                    "bullet": state == bullet,
                    "indent": len(current_indent),
                    "lines": current_chunk
                }
                current_chunk = []
        else:
            current_chunk.append(line)

    yield {
        "bullet": state == bullet,
        "indent": len(current_indent),
        "lines": current_chunk
    }


def markup(recs):
    for rec in recs:
        code = False
        current_chunk = []
        for line in rec["lines"]:

            if line.startswith("{{{"):
                code = True
                current_chunk.extend(["::", ""])

            elif line.startswith("}}}"):
                code = False
            elif code:
                current_chunk.append("    " + line)
            else:
                if line == "----" or \
                    line.startswith("[[PageOutline"):
                    continue
                line = re.sub(r"`(.+?)`", lambda m: "``%s``" % m.group(1), line)
                line = re.sub(r"'''(.+?)'''", lambda m: "**%s**" % m.group(1), line)
                line = re.sub(r"''(.+?)'", lambda m: "*%s*" % m.group(1), line)
                line = re.sub(r'\[(http://\S+) (.*)\]',
                        lambda m: "`%s <%s>`_" % (m.group(2), m.group(1)),
                        line
                    )
                if line.startswith("=") and line.endswith("="):
                    line = output_header(line)
                current_chunk.append(line)

        rec['lines'] = current_chunk
        yield rec


#            m = re.match(r'^(\s*){{{\s*$', line)

#            if line.startswith("=") and line.endswith("="):
#                yield output_header(line)
#                continue

#        if state == code:
#            if re.match(r'^\s*#\!', line):
#                continue

#            if re.match(r'^\s*}}}\s*$', line):
#                state = prevstate
#                continue


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
        return "%s\n%s\n%s" % (
                    "=" * len(m.group(2)),
                    m.group(2),
                    "=" * len(m.group(2))
                )
    char = {
        2: "=",
        3: "-",
        4: "^"
    }[depth]
    return "%s\n%s" % (
                m.group(2),
                char * len(m.group(2))
            )

if __name__ == '__main__':
    fname = sys.argv[1]
    for rec in markup(structure(fname)):
        print rec
