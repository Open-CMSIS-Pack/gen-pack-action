#!/usr/bin/env python3
"""Resolve the action's Doxygen version without executing documentation scripts."""

import os
from pathlib import Path
import re
import shlex
import sys

from shell_script import script_lines


VERSION = re.compile(r"[0-9]+(?:\.[0-9]+)+")
VARIABLE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
ASSIGNMENT = re.compile(r"(?:export\s+|readonly\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)")
ARGUMENT = re.compile(r'''("[^"\n]*"|'[^'\n]*'|[^\s'";]+)(?:[ \t]+\#.*)?''')


def read_argument(expression):
    """Read one simple shell word, preserving whether single quotes prevent expansion."""
    match = ARGUMENT.fullmatch(expression.strip())
    if not match:
        raise ValueError("expected one literal version or simple Bash variable")
    word = match.group(1)
    single_quoted = word.startswith("'")
    if word.startswith(('"', "'")):
        word = word[1:-1]
    return word, single_quoted


def literal_version(value):
    """Validate a dot-separated numeric version without evaluating shell expressions."""
    if not VERSION.fullmatch(value):
        raise ValueError("the required Doxygen version must be a literal numeric version")
    return value


def version_argument(expression, assignments):
    """Resolve a literal version or a variable with one preceding literal assignment."""
    argument, single_quoted = read_argument(expression)
    variable = VARIABLE.fullmatch(argument)
    if not variable:
        return literal_version(argument)
    # Single-quoted Bash strings do not expand variables.
    if single_quoted:
        raise ValueError("single-quoted version variables are not expanded by Bash")
    name = variable.group(1) or variable.group(2)
    expressions = assignments.get(name, [])
    if len(expressions) != 1:
        raise ValueError(f"{name} must have one literal assignment before find_doxygen")
    argument, _ = read_argument(expressions[0])
    return literal_version(argument)


def required_version(script):
    """Read standalone find_doxygen calls and their preceding literal assignments."""
    assignments = {}
    versions = set()
    source = script.read_text(encoding="utf-8")
    for number, line in script_lines(source):
        statement = line.strip()
        assignment = ASSIGNMENT.fullmatch(statement)
        if assignment:
            name, expression = assignment.groups()
            assignments.setdefault(name, []).append(expression)
            continue
        if re.match(r"find_doxygen\s*\(\s*\)", statement):
            continue
        if not re.match(r"find_doxygen(?:\s|$)", statement):
            continue
        try:
            versions.add(version_argument(statement[len("find_doxygen"):], assignments))
        except ValueError as error:
            raise ValueError(f"{script}:{number}: {error}") from error
    if not versions:
        raise ValueError(f"{script}: no standalone find_doxygen version requirement found")
    if len(versions) != 1:
        raise ValueError(f"{script}: conflicting find_doxygen version requirements")
    return versions.pop()


def resolve_version(version, gen_doc_script):
    """Use the explicit input or inspect the script path relative to the current directory."""
    if not version or "\n" in version or "\r" in version:
        raise ValueError("doxygen-version must be a nonempty, single-line value")
    if version != "auto":
        return version
    arguments = shlex.split(gen_doc_script)
    if not arguments:
        raise ValueError("doxygen-version: auto requires gen-doc-script")
    return required_version(Path(arguments[0]))


def main():
    """Write the resolved step output or fail the action with a useful diagnostic."""
    try:
        version = resolve_version(os.environ["DOXYGEN_VERSION"], os.environ.get("GEN_DOC_SCRIPT", ""))
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write(f"version={version}\n")
    except (OSError, UnicodeError, ValueError) as error:
        message = str(error).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::error::Unable to resolve Doxygen version: {message}", file=sys.stderr)
        return 1
    print(f"Doxygen version: {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
