"""Exercise the action's version resolver through its real command-line interface."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


RESOLVER = Path(__file__).resolve().parents[1] / "scripts" / "resolve-doxygen-version.py"


@pytest.fixture
def resolve(tmp_path):
    """Provide a CLI runner with an isolated working directory for each test case."""
    def run_resolver(source=None, version="auto", command="./gen_doc.sh",
                     environment=None, script_path="gen_doc.sh"):
        """Write the script, run the resolver, and return its process and step output."""
        script = tmp_path / script_path
        output = tmp_path / "output"

        if source is not None:
            script.parent.mkdir(parents=True, exist_ok=True)
            script.write_text(source, encoding="utf-8")
        output.write_text("", encoding="utf-8")

        env = dict(os.environ, DOXYGEN_VERSION=version, GEN_DOC_SCRIPT=command,
                   GITHUB_OUTPUT=str(output))
        env.update(environment or {})
        process = subprocess.run([sys.executable, str(RESOLVER)], cwd=tmp_path,
                                 env=env, capture_output=True, text=True)
        return process, output.read_text(encoding="utf-8")

    return run_resolver


@pytest.mark.parametrize("version", ["1.9.6", "1.17.0", "none"])
def test_explicit_version_and_none_do_not_require_a_script(resolve, version):
    process, output = resolve(version=version, command="")
    assert process.returncode == 0, process.stderr
    assert output == f"version={version}\n"


@pytest.mark.parametrize(
    "argument",
    ["1.17.0", '"1.17.0"', "'1.17.0'"],
    ids=["unquoted", "double-quoted", "single-quoted"],
)
def test_literal_versions(resolve, argument):
    process, output = resolve(f"find_doxygen {argument} # required\n")
    assert process.returncode == 0, process.stderr
    assert output == "version=1.17.0\n"


@pytest.mark.parametrize(
    "declaration", ["", "export ", "readonly "], ids=["plain", "export", "readonly"],
)
@pytest.mark.parametrize(
    "value",
    ["1.13.2", '"1.13.2"', "'1.13.2'"],
    ids=["unquoted", "double-quoted", "single-quoted"],
)
@pytest.mark.parametrize(
    "reference",
    ["$REQ_DXY_VERSION", "${REQ_DXY_VERSION}", '"${REQ_DXY_VERSION}"'],
    ids=["simple", "braced", "quoted-braced"],
)
def test_bash_variable_assignments_and_references(resolve, declaration, value, reference):
    process, output = resolve(
        f"  {declaration}REQ_DXY_VERSION={value} # literal\n"
        f"\tfind_doxygen {reference}\n")
    assert process.returncode == 0, process.stderr
    assert output == "version=1.13.2\n"


def test_script_arguments_and_quoted_path(resolve):
    process, output = resolve(
        'find_doxygen "1.17.0"\n',
        command='"./docs with spaces/gen_doc.sh" --no-linkcheck',
        script_path="docs with spaces/gen_doc.sh",
    )
    assert process.returncode == 0, process.stderr
    assert output == "version=1.17.0\n"


def test_comments_and_unrelated_commands_are_ignored(resolve):
    process, output = resolve(
        '# find_doxygen "9.9.9"\necho "find_doxygen 2.0.0"\n'
        'OTHER=$(anything --dynamic)\nREQ="1.9.6"\nfind_doxygen "$REQ"\n')
    assert process.returncode == 0, process.stderr
    assert output == "version=1.9.6\n"


@pytest.mark.parametrize(
    "source",
    [
        pytest.param('REQ="1.9.6"\r\nfind_doxygen \\\r\n "$REQ"\r\n', id="crlf"),
        pytest.param('find_doxygen 1.9.\\\n6\n', id="unquoted-version"),
        pytest.param('find_doxygen "1.9.\\\n6"\n', id="double-quoted-version"),
        pytest.param('REQ="1.9.\\\n6"\nfind_doxygen "$REQ"\n', id="assignment"),
        pytest.param('find_\\\ndoxygen "1.9.6"\n', id="command-name"),
    ],
)
def test_line_continuation_and_crlf(resolve, source):
    process, output = resolve(source)
    assert process.returncode == 0, process.stderr
    assert output == "version=1.9.6\n"


@pytest.mark.parametrize("comment", ["# explanation", ": # explanation"])
@pytest.mark.parametrize(
    "requirement",
    [
        pytest.param('find_doxygen "1.17.0"\n', id="direct-call"),
        pytest.param('REQ="1.17.0"\nfind_doxygen "$REQ"\n', id="assignment"),
    ],
)
def test_comment_backslashes_do_not_hide_requirements(resolve, comment, requirement):
    process, output = resolve(f"{comment} \\\n" + requirement)
    assert process.returncode == 0, process.stderr
    assert output == "version=1.17.0\n"


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("find_doxygen '1.17.\\\n0'\n", id="direct-call"),
        pytest.param("REQ='1.17.\\\n0'\nfind_doxygen \"$REQ\"\n", id="assignment"),
    ],
)
def test_single_quoted_continuations_are_not_numeric_versions(resolve, source):
    process, output = resolve(source)
    assert process.returncode != 0
    assert "::error::Unable to resolve Doxygen version:" in process.stderr
    assert output == ""


def test_escaped_backslashes_do_not_continue_lines(resolve):
    process, output = resolve('echo ignored \\\\\nfind_doxygen "1.17.0"\n')
    assert process.returncode == 0, process.stderr
    assert output == "version=1.17.0\n"


@pytest.mark.parametrize(
    "source",
    [
        pytest.param('echo "example:\nfind_doxygen 9.9.9\n"\n', id="double-quoted-string"),
        pytest.param("echo 'example:\nfind_doxygen 9.9.9\n'\n", id="single-quoted-string"),
        pytest.param("cat <<EOF\nfind_doxygen 9.9.9\nEOF\n", id="unquoted-heredoc"),
        pytest.param("cat <<'EOF'\nfind_doxygen 9.9.9\nEOF\n", id="quoted-heredoc"),
        pytest.param('cat <<-"EOF"\n\tfind_doxygen 9.9.9\n\tEOF\n', id="tab-stripped-heredoc"),
    ],
)
def test_multiline_strings_and_heredocs_do_not_supply_requirements(resolve, source):
    process, output = resolve(source)
    assert process.returncode != 0
    assert output == ""

    process, output = resolve(source + 'find_doxygen "1.17.0"\n')
    assert process.returncode == 0, process.stderr
    assert output == "version=1.17.0\n"


@pytest.mark.parametrize(
    "word, delimiter",
    [
        pytest.param("END-HELP", "END-HELP", id="hyphenated"),
        pytest.param("123", "123", id="numeric"),
        pytest.param(r"\EOF", "EOF", id="escaped"),
        pytest.param('E"OF"', "EOF", id="partly-double-quoted"),
        pytest.param("E'OF'", "EOF", id="partly-single-quoted"),
        pytest.param("''", "", id="empty-single-quoted"),
        pytest.param('""', "", id="empty-double-quoted"),
        pytest.param(r'"END\-HELP"', r"END\-HELP", id="literal-backslash-in-double-quotes"),
        pytest.param(r'"END\$HELP"', "END$HELP", id="escaped-dollar-in-double-quotes"),
        pytest.param("EO\\\nF", "EOF", id="continued-delimiter"),
        pytest.param("\\\n EOF", "EOF", id="continuation-before-delimiter"),
        pytest.param("123>/dev/null", "123", id="adjacent-redirection"),
    ],
)
@pytest.mark.parametrize("following_call", [False, True], ids=["body-only", "real-call"])
def test_complete_heredoc_delimiters_hide_only_their_bodies(resolve, word, delimiter, following_call):
    source = f"cat <<{word}\nfind_doxygen 9.9.9\n{delimiter}\n"
    if following_call:
        source += 'find_doxygen "1.17.0"\n'

    process, output = resolve(source)

    if following_call:
        assert process.returncode == 0, process.stderr
        assert output == "version=1.17.0\n"
    else:
        assert process.returncode != 0
        assert "no standalone find_doxygen version requirement found" in process.stderr
        assert output == ""


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("cat <<'EOF'\ncontinued \\\nEOF\n", id="quoted-body"),
        pytest.param(
            "cat <<EOF\ncontinued \\\nEOF\nfind_doxygen 9.9.9\nEOF\n", id="unquoted-body"),
        pytest.param("cat <<EOF\nEO\\\nF\n", id="continued-end-delimiter"),
        pytest.param(
            "cat <<'EOF'\nEO\\\nF\nfind_doxygen 9.9.9\nEOF\n", id="quoted-end-delimiter"),
        pytest.param(
            "cat <<123 <<-'END-HELP'\nfind_doxygen 9.9.9\n123\n"
            "\tfind_doxygen 9.9.8\n\tEND-HELP\n", id="multiple-bodies"),
    ],
)
def test_heredoc_continuations_respect_delimiter_quoting(resolve, source):
    process, output = resolve(source + 'find_doxygen "1.17.0"\n')
    assert process.returncode == 0, process.stderr
    assert output == "version=1.17.0\n"


@pytest.mark.parametrize(
    "expression",
    ["((bits = 1 << 2))", "bits=$((1 << 2))"],
    ids=["arithmetic-command", "arithmetic-expansion"],
)
def test_arithmetic_shifts_are_not_heredocs(resolve, expression):
    process, output = resolve(expression + '\nfind_doxygen "1.17.0"\n')
    assert process.returncode == 0, process.stderr
    assert output == "version=1.17.0\n"


def test_errors_after_continuations_report_physical_line_numbers(resolve):
    process, output = resolve('echo ignored \\\n continuation\nfind_doxygen dynamic\n')
    assert process.returncode != 0
    assert "gen_doc.sh:3:" in process.stderr
    assert output == ""


@pytest.mark.parametrize(
    "argument",
    ['"example"', "'example'", "example"],
    ids=["double-quoted", "single-quoted", "unquoted"],
)
@pytest.mark.parametrize("spacing", [" ", ""], ids=["spaced", "adjacent"])
def test_here_strings_do_not_hide_following_requirements(resolve, argument, spacing):
    process, output = resolve(
        f"read -r ignored <<<{spacing}{argument}\n"
        'find_doxygen "1.17.0"\n')
    assert process.returncode == 0, process.stderr
    assert output == "version=1.17.0\n"


@pytest.mark.parametrize("spacing", [" ", "\t"], ids=["space", "tab"])
@pytest.mark.parametrize("brace_separator", [" ", "\n"], ids=["inline-brace", "next-line-brace"])
def test_function_declarations_are_not_version_calls(resolve, spacing, brace_separator):
    process, output = resolve(
        f"find_doxygen{spacing}(){brace_separator}{{\n"
        "  :\n"
        "}\n"
        'find_doxygen "1.17.0"\n')
    assert process.returncode == 0, process.stderr
    assert output == "version=1.17.0\n"


def test_repeated_matching_calls(resolve):
    process, output = resolve('find_doxygen 1.9.6\nfind_doxygen "1.9.6"\n')
    assert process.returncode == 0, process.stderr
    assert output == "version=1.9.6\n"


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("", id="empty-script"),
        pytest.param('# find_doxygen 1.17.0\n', id="comment-only"),
        pytest.param("find_doxygen\n", id="missing-version"),
        pytest.param("find_doxygen 1.17.0 extra\n", id="extra-argument"),
        pytest.param('find_doxygen "$MISSING"\n', id="missing-assignment"),
        pytest.param('find_doxygen "$REQ"\nREQ="1.17.0"\n', id="assignment-after-call"),
        pytest.param(
            'REQ="1.9.6"\nREQ="1.17.0"\nfind_doxygen "$REQ"\n', id="reassigned-variable"),
        pytest.param('REQ="1.17.0"\nfind_doxygen \'$REQ\'\n', id="single-quoted-variable"),
        pytest.param('REQ="1.17.0"\nfind_doxygen "${REQ:-1.9.6}"\n', id="variable-fallback"),
        pytest.param('REQ="$EXTERNAL"\nfind_doxygen "$REQ"\n', id="nonliteral-assignment"),
        pytest.param('REQ=1.17.0#not-a-comment\nfind_doxygen "$REQ"\n', id="embedded-hash"),
        pytest.param('find_doxygen "\'1.17.0\'"\n', id="nested-quotes"),
        pytest.param('find_doxygen "1.17.0\n', id="unterminated-quote"),
        pytest.param("find_doxygen 1.9.6\nfind_doxygen 1.17.0\n", id="conflicting-versions"),
    ],
)
def test_unresolvable_requirements_fail_without_output(resolve, source):
    process, output = resolve(source, environment={"MISSING": "1.17.0", "EXTERNAL": "1.17.0"})
    assert process.returncode != 0
    assert "::error::Unable to resolve Doxygen version:" in process.stderr
    assert output == ""


@pytest.mark.parametrize(
    "command",
    ["", "missing.sh", ".", '"unterminated'],
    ids=["empty-command", "missing-file", "directory", "unterminated-quote"],
)
def test_missing_command_and_unreadable_script_fail(resolve, command):
    process, output = resolve(command=command)
    assert process.returncode != 0
    assert output == ""


@pytest.mark.parametrize(
    "source, expected_status",
    [
        pytest.param(
            'touch executed\nREQ="1.17.0"\nfind_doxygen "$REQ"\n', 0, id="script-command"),
        pytest.param(
            'REQ="$(touch executed; echo 1.17.0)"\nfind_doxygen "$REQ"\n', 1,
            id="command-substitution"),
        pytest.param(
            'REQ=`touch executed; echo 1.17.0`\nfind_doxygen "$REQ"\n', 1,
            id="backtick-substitution"),
    ],
)
def test_scripts_and_command_substitutions_are_never_executed(resolve, tmp_path, source, expected_status):
    process, _ = resolve(source)
    assert not (tmp_path / "executed").exists()
    assert process.returncode == expected_status, process.stderr


def test_sanity_script_exposes_its_actual_version(resolve):
    process, output = resolve(command=str(RESOLVER.parents[1] / "sanity-check" / "check-doxygen.sh"))
    assert process.returncode == 0, process.stderr
    assert output == "version=1.9.6\n"
