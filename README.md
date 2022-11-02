# gen-pack-action

GitHub workflow action to generate documentation and packs

The composite action runs the usual steps for generating documentation
and pack archives:

1. Installs required tools like doxygen and packchk.
2. Generates the documentation if a generator script is provided.
3. Checks hyperlinks in the generated documentation if a checker script is provided.
4. Archives the documentation if the output path is provided.
5. Generates the Open-CMSIS-Pack pack if a generator script is provided.
6. Archives the generated pack if the output folder is provided.
7. Publishes the documentation to GH-Pages if documentation path and branch are provided.

# Usage

```yaml
- uses: Open-CMSIS-Pack/gen-pack-action@main
  with:
    doxygen-version: 1.9.2                                  # default
    packchk-version: 1.3.95                                 # default
    gen-doc-script: ./DoxyGen/gen_doc.sh                    # skipped by default
    check-links-script: ./Documentation/check_links.sh      # skipped by default
    doc-path: ./Documentation/html                          # skipped by default
    gen-pack-script: ./gen_pack.sh                          # skipped by default
    gen-pack-output: ./output                               # skipped by default
    gh-pages-branch: gh-pages                               # default
```

## Advanced usage

### Doxygen download

The URL Doxygen is downloaded from can be overwritten with the action input parameter
`doxygen-url` which defaults to
`https://sourceforge.net/projects/doxygen/files/rel-{VERSION}/doxygen-{VERSION}.linux.bin.tar.gz/download`.
The `{VERSION}` pattern is substituted with the value provided in `doxygen-version`.
