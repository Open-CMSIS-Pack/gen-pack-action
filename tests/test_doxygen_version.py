"""Exercise the action's version resolver through its real command-line interface."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


RESOLVER = Path(__file__).resolve().parents[1] / "scripts" / "resolve-doxygen-version.py"


class DoxygenVersionTests(unittest.TestCase):
    """Cover explicit inputs, static Bash requirements, and early failures."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.script = self.root / "gen_doc.sh"
        self.output = self.root / "output"

    def resolve(self, source=None, version="auto", command="./gen_doc.sh", environment=None):
        """Run from the configured working directory and return the actual step output."""
        if source is not None:
            self.script.write_text(source, encoding="utf-8")
        self.output.write_text("", encoding="utf-8")
        env = dict(os.environ, DOXYGEN_VERSION=version, GEN_DOC_SCRIPT=command,
                   GITHUB_OUTPUT=str(self.output))
        env.update(environment or {})
        process = subprocess.run([sys.executable, str(RESOLVER)], cwd=self.root,
                                 env=env, capture_output=True, text=True)
        return process, self.output.read_text(encoding="utf-8")

    def test_explicit_version_and_none_do_not_require_a_script(self):
        for version in ["1.9.6", "1.17.0", "none"]:
            with self.subTest(version=version):
                process, output = self.resolve(version=version, command="")
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(output, f"version={version}\n")

    def test_literal_versions(self):
        for argument in ["1.17.0", '"1.17.0"', "'1.17.0'"]:
            with self.subTest(argument=argument):
                process, output = self.resolve(f"find_doxygen {argument} # required\n")
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(output, "version=1.17.0\n")

    def test_bash_variable_assignments_and_references(self):
        for declaration in ["", "export ", "readonly "]:
            for value in ["1.13.2", '"1.13.2"', "'1.13.2'"]:
                for reference in ["$REQ_DXY_VERSION", "${REQ_DXY_VERSION}", '"${REQ_DXY_VERSION}"']:
                    with self.subTest(declaration=declaration, value=value, reference=reference):
                        process, output = self.resolve(
                            f"  {declaration}REQ_DXY_VERSION={value} # literal\n"
                            f"\tfind_doxygen {reference}\n")
                        self.assertEqual(process.returncode, 0, process.stderr)
                        self.assertEqual(output, "version=1.13.2\n")

    def test_script_arguments_and_quoted_path(self):
        self.script = self.root / "docs with spaces" / "gen_doc.sh"
        self.script.parent.mkdir()
        process, output = self.resolve('find_doxygen "1.17.0"\n',
            command='"./docs with spaces/gen_doc.sh" --no-linkcheck')
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(output, "version=1.17.0\n")

    def test_comments_and_unrelated_commands_are_ignored(self):
        process, output = self.resolve(
            '# find_doxygen "9.9.9"\necho "find_doxygen 2.0.0"\n'
            'OTHER=$(anything --dynamic)\nREQ="1.9.6"\nfind_doxygen "$REQ"\n')
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(output, "version=1.9.6\n")

    def test_line_continuation_and_crlf(self):
        process, output = self.resolve('REQ="1.9.6"\r\nfind_doxygen \\\r\n "$REQ"\r\n')
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(output, "version=1.9.6\n")

    def test_multiline_strings_and_heredocs_do_not_supply_requirements(self):
        for source in [
            'echo "example:\nfind_doxygen 9.9.9\n"\n',
            "echo 'example:\nfind_doxygen 9.9.9\n'\n",
            "cat <<EOF\nfind_doxygen 9.9.9\nEOF\n",
            "cat <<'EOF'\nfind_doxygen 9.9.9\nEOF\n",
            'cat <<-"EOF"\n\tfind_doxygen 9.9.9\n\tEOF\n',
        ]:
            with self.subTest(source=source):
                process, output = self.resolve(source)
                self.assertNotEqual(process.returncode, 0)
                self.assertEqual(output, "")
                process, output = self.resolve(source + 'find_doxygen "1.17.0"\n')
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(output, "version=1.17.0\n")

    def test_repeated_matching_calls(self):
        process, output = self.resolve('find_doxygen 1.9.6\nfind_doxygen "1.9.6"\n')
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(output, "version=1.9.6\n")

    def test_unresolvable_requirements_fail_without_output(self):
        for source in [
            "", '# find_doxygen 1.17.0\n', "find_doxygen\n",
            "find_doxygen 1.17.0 extra\n", 'find_doxygen "$MISSING"\n',
            'find_doxygen "$REQ"\nREQ="1.17.0"\n',
            'REQ="1.9.6"\nREQ="1.17.0"\nfind_doxygen "$REQ"\n',
            'REQ="1.17.0"\nfind_doxygen \'$REQ\'\n',
            'REQ="1.17.0"\nfind_doxygen "${REQ:-1.9.6}"\n',
            'REQ="$EXTERNAL"\nfind_doxygen "$REQ"\n',
            'REQ=1.17.0#not-a-comment\nfind_doxygen "$REQ"\n',
            'find_doxygen "\'1.17.0\'"\n', 'find_doxygen "1.17.0\n',
            "find_doxygen 1.9.6\nfind_doxygen 1.17.0\n",
        ]:
            with self.subTest(source=source):
                process, output = self.resolve(source, environment={"MISSING":"1.17.0", "EXTERNAL":"1.17.0"})
                self.assertNotEqual(process.returncode, 0)
                self.assertIn("::error::Unable to resolve Doxygen version:", process.stderr)
                self.assertEqual(output, "")

    def test_missing_command_and_unreadable_script_fail(self):
        for command in ["", "missing.sh", ".", '"unterminated']:
            with self.subTest(command=command):
                process, output = self.resolve(command=command)
                self.assertNotEqual(process.returncode, 0)
                self.assertEqual(output, "")

    def test_scripts_and_command_substitutions_are_never_executed(self):
        for source in [
            'touch executed\nREQ="1.17.0"\nfind_doxygen "$REQ"\n',
            'REQ="$(touch executed; echo 1.17.0)"\nfind_doxygen "$REQ"\n',
            'REQ=`touch executed; echo 1.17.0`\nfind_doxygen "$REQ"\n',
        ]:
            with self.subTest(source=source):
                process, _ = self.resolve(source)
                self.assertFalse((self.root / "executed").exists())
                if "$(" in source or "`" in source:
                    self.assertNotEqual(process.returncode, 0)

    def test_sanity_script_exposes_its_actual_version(self):
        process, output = self.resolve(command=str(RESOLVER.parents[1] / "sanity-check" / "check-doxygen.sh"))
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(output, "version=1.9.6\n")


if __name__ == "__main__":
    unittest.main()
