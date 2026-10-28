"""Read logical shell lines while excluding multiline literals and here-documents."""

import re


HEREDOC_PREFIX = re.compile(r"<<(?:\\\n)*(-?)(?:[ \t]|\\\n)*")
DELIMITER_PART = re.compile(r"""
    (?P<bare>[^ \t\n;|&()<>'"\\]+)
    | (?P<single>'[^']*')
    | (?P<double>"(?:\\[\s\S]|[^"\\])*")
    | (?P<escaped>\\(?:[\s\S]|$))
""", re.VERBOSE)
DOUBLE_QUOTED_ESCAPE = re.compile(r'\\([$`"\\\n])')


def delimiter_part(match):
    """Remove quoting from one delimiter fragment without expanding its contents."""
    part = match.group()
    if match.lastgroup == "single":
        return part[1:-1], True
    if match.lastgroup == "double":
        value = DOUBLE_QUOTED_ESCAPE.sub(lambda escape: escape[1].replace("\n", ""), part[1:-1])
        return value, True
    if match.lastgroup == "escaped" and len(part) > 1:
        return part[1:].replace("\n", ""), part[1] != "\n"
    return part, False


def read_heredoc(source, position, heredocs):
    """Queue a complete delimiter word after quote removal, without shell expansion."""
    prefix = HEREDOC_PREFIX.match(source, position)
    position = prefix.end()
    start = position
    delimiter = []
    quoted = False
    while match := DELIMITER_PART.match(source, position):
        value, part_quoted = delimiter_part(match)
        delimiter.append(value)
        quoted |= part_quoted
        position = match.end()
    if position == start or source[position:position + 1] in ("'", '"'):
        raise ValueError("expected a complete here-document delimiter")
    heredocs.append(("".join(delimiter), bool(prefix[1]), quoted))
    return position


def line_end(source, position):
    """Find the next newline, returning the end of the source if none remains."""
    newline = source.find("\n", position)
    return len(source) if newline == -1 else newline


def continued_heredoc_line(line, quoted):
    """Check whether an unquoted body line ends in an unescaped backslash-newline."""
    content = line.removesuffix("\n")
    backslashes = len(content) - len(content.rstrip("\\"))
    return not quoted and line.endswith("\n") and backslashes % 2 == 1


def heredoc_line(source, position, quoted):
    """Read one body line, joining continuations only for an unquoted delimiter."""
    fragments = []
    while position < len(source):
        end = min(line_end(source, position) + 1, len(source))
        line = source[position:end]
        position = end
        if continued_heredoc_line(line, quoted):
            fragments.append(line[:-2])
            continue
        fragments.append(line.removesuffix("\n"))
        break
    return "".join(fragments), position


def skip_heredoc(source, position, delimiter, strip_tabs, quoted):
    """Advance past one body and its delimiter, applying the tab-stripping rule."""
    while position < len(source):
        candidate, position = heredoc_line(source, position, quoted)
        if strip_tabs:
            candidate = candidate.lstrip("\t")
        if candidate == delimiter:
            break
    return position


def skip_heredocs(source, position, heredocs):
    """Skip queued bodies in their declaration order, then empty the queue."""
    for delimiter, strip_tabs, quoted in heredocs:
        position = skip_heredoc(source, position, delimiter, strip_tabs, quoted)
    heredocs.clear()
    return position


class ScriptScanner:
    """Read logical shell lines while retaining quote, arithmetic and heredoc state."""

    def __init__(self, source):
        """Start scanning at the first physical line without executing shell code."""
        self.source = source
        self.position = 0
        self.number = 1
        self.quote = None
        self.heredocs = []
        self.line = []
        self.arithmetic_depth = 0

    def take(self, end):
        """Consume source text and update its physical line number."""
        fragment = self.source[self.position:end]
        self.number += fragment.count("\n")
        self.position = end
        return fragment

    def append(self, end):
        """Consume source text into the current logical line."""
        self.line.append(self.take(end))

    def read_escape(self):
        """Consume an escape or continuation unless single quotes make it literal."""
        if self.quote == "'" or self.source[self.position] != "\\":
            return False
        end = self.position + 2
        if self.source.startswith("\\\n", self.position):
            self.take(end)
        else:
            self.append(end)
        return True

    def read_character(self):
        """Advance one shell fragment according to the current quoting context."""
        if self.read_escape():
            return
        character = self.source[self.position]
        if self.quote:
            if character == self.quote:
                self.quote = None
        elif character in "\"'`":
            self.quote = character
        elif self.arithmetic_depth:
            self.arithmetic_depth += {"(": 1, ")": -1}.get(character, 0)
        else:
            self.read_operator()
            return
        self.append(self.position + 1)

    def starts_comment(self):
        """Check for a comment marker at the start of an unquoted shell word."""
        return self.source[self.position] == "#" and (not self.line or self.line[-1][-1] in " \t;|&()")

    def read_operator(self):
        """Read an unquoted operator, a whole comment, or an ordinary character."""
        if self.source.startswith("((", self.position):
            # Arithmetic commands and expansions use << as a shift operator.
            self.arithmetic_depth = 2
            self.append(self.position + 2)
        elif self.starts_comment():
            self.append(line_end(self.source, self.position))
        elif self.source.startswith("<<<", self.position):
            # Here-strings have no delimiter or following body to skip.
            self.append(self.position + 3)
        elif self.source.startswith("<<", self.position):
            self.append(read_heredoc(self.source, self.position, self.heredocs))
        else:
            self.append(self.position + 1)

    def read_line(self):
        """Read one logical line and consume any following here-document bodies."""
        self.line = []
        while self.position < len(self.source) and self.source[self.position] != "\n":
            self.read_character()
        value = "".join(self.line)
        if self.source[self.position:self.position + 1] == "\n":
            self.take(self.position + 1)
            self.take(skip_heredocs(self.source, self.position, self.heredocs))
        return value


def script_lines(source):
    """Yield commands with valid continuations joined, skipping multiline literal text."""
    scanner = ScriptScanner(source)
    while scanner.position < len(source):
        number = scanner.number
        starts_unquoted = scanner.quote is None
        line = scanner.read_line()
        if starts_unquoted:
            yield number, line
