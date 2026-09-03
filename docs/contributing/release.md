# Releasing

Releases are published to [PyPI](https://pypi.org/project/pywebview/) by the
[`release.yml`](https://github.com/r0x0r/pywebview/blob/master/.github/workflows/release.yml)
workflow when a GitHub release is published.

## Versioning

The version is derived from git tags by
[setuptools_scm](https://setuptools-scm.readthedocs.io/) and written to `webview/_version.py` at
build time. There is no version number to edit anywhere in the tree — do not commit
`webview/_version.py`, it is generated and git-ignored.

A tag of `6.3` produces version `6.3`. Between tags, builds get a development version such as
`6.3.1.dev12+g8aeb870`.

## Cutting a release

1. Move the `## Unreleased` heading in [docs/CHANGELOG.md](../CHANGELOG.md) to the version being
   released and add the release date:

   ``` markdown
   ## 6.3

   _Released 03/09/2026_
   ```

2. Commit and push to `master`.

3. Tag the commit and push the tag:

   ``` bash
   git tag 6.3
   git push origin 6.3
   ```

4. [Create a GitHub release](https://github.com/r0x0r/pywebview/releases/new) for the tag and
   publish it.

Publishing the release triggers two workflows:

* `release.yml` builds the sdist and wheel, runs `twine check --strict` on them, and uploads them
  to PyPI.
* `docs.yaml` merges `master` into the `docs` branch, from which the website is built.

A manual `workflow_dispatch` run of `release.yml` builds and checks the distributions without
uploading anything, which is a useful dry run before tagging.

## One-time PyPI set-up

The workflow uses [trusted publishing](https://docs.pypi.org/trusted-publishers/), so no PyPI API
token is stored in the repository. It has to be configured once, otherwise the publish step fails
with `invalid-publisher`.

On [pypi.org](https://pypi.org), go to the `pywebview` project → *Manage* → *Publishing* → *Add a
new publisher* → *GitHub*, and enter:

| Field | Value |
| --- | --- |
| Owner | `r0x0r` |
| Repository name | `pywebview` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

Then, on GitHub, go to *Settings* → *Environments* and create an environment named `pypi` if it
does not already exist. Adding a required reviewer to it makes every upload wait for a manual
approval, which is worth considering.

## Publishing by hand

If trusted publishing is unavailable, a release can still be built and uploaded manually:

``` bash
git checkout 6.3
pip install build twine
rm -rf dist
python -m build
twine check --strict dist/*
twine upload dist/*
```

This requires a PyPI API token in `~/.pypirc` or `TWINE_PASSWORD`.
