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

## Usage

```yaml
- uses: Open-CMSIS-Pack/gen-pack-action@main
  with:
    doxygen-version: 1.9.6                                  # default
    packchk-version: 1.3.95                                 # default
    gen-doc-script: ./DoxyGen/gen_doc.sh                    # skipped by default
    check-links-script: ./Documentation/check_links.sh      # skipped by default
    doc-path: ./Documentation/html                          # skipped by default
    gen-pack-script: ./gen_pack.sh                          # skipped by default
    gen-pack-output: ./output                               # skipped by default
    gh-pages-branch: gh-pages                               # default
    gh-pages-deploy: gh-pages.yml                           # default
```

> **Attention for Windows users**
>
> On Windows Bash scripts are executable without special handling. This
> does not hold true once moving the files to a Linux machine. To assure
> the eXecute permission gets set on Linux, run the following Git command
> on the Windows machine and commit the change:
>
> `git update-index --chmod=+x <script>`

As a starting point you can use the [workflow template](workflows/pack.yml) and add it to your projects
GitHub repository under `.github/workflows/`. For details about documentation handling, see [below](#publish-to-github-pages).

## Advanced usage

### Doxygen download

If Doxygen is not required one can skip download and installation by setting `doxygen-version: none`.

The URL Doxygen is downloaded from can be overwritten with the action input parameter
`doxygen-url` which defaults to
`https://sourceforge.net/projects/doxygen/files/rel-{VERSION}/doxygen-{VERSION}.linux.bin.tar.gz/download`.
The `{VERSION}` pattern is substituted with the value provided in `doxygen-version`.

### Publish to GitHub Pages

Publishing documentation to GitHub Pages is handled automatically via the settings

- `gen-doc-script` for generating if required, leave empty to skip generation.
- `doc-path` for archiving documentation, leave empty to skip archiving/publishing.
- `gh-pages-branch` for publishing to GitHub Pages, set to empty to skip publishing.
- `gh-pages-deploy` for trigger GitHub Pages deploy workflow, set to emtpy to skip.

Once the settings are given, the workflow will commit the generated documentation from `doc-path`
into a subfolder onto the `gh-pages-branch`. After pushing back the `gh-pages-deploy` is triggered
to issue actual pages deployment. Check your repositories settings `Pages > Build and Deployment > Source`
is set to `GitHub Action`.

The repository needs to be prepared for GitHub Pages as the following:

- Create orphaned `gh-pages` branch:

  ```sh
  # git checkout --orphan gh-pages
  Switched to a new branch 'gh-pages'
  # git reset
  ```

- Provide initial content taken from the [templates](workflows/):
  - The [`.github/workflows/gh-pages.yml`](workflows/gh-pages.yml) deploy workflow.
  - An [`index.html`](publish-doc/index.html) with front page or redirection to `latest`.
  - The [`update_versions.sh`](publish-doc/update_versions.sh) shell script.
    Assure execute flag is set. On Windows use `git update-index --chmod=+x <script>` to record the execte flag, properly.
  - The [`versions.js.in`](publish-doc/version.js.in) JavaScript template.
  - Some initial content e.g. for `main` branch in folder `main`.
  - A `latest` symlink pointing to initial content folder.
- Commit and push documentation branch:

  ```sh
  # git add .github index.html update_versions.sh versions.js.in main latest
  # git commit -m "Initial contribution"
  # git push origin gh-pages:gh-pages
  ```

- Switch back to `main` branch and add the [`.github/workflows/gh-pages.yml`](workflows/gh-pages.yml) deploy workflow there as well:

  ```sh
  # git checkout main
  Switched to branch 'main'
  # git add .github/workflows/gh-pages.yml
  # git commit -m "Add GitHub Pages deploy workflow"
  # git push
  ```
