To cut a new release

- prepare release notes for this release by inspecting the
  [milestone](https://github.com/gwpy/pyomicron/milestones) on github.com

- create a git tag

  ```bash
  git tag -a -s vX.Y.Z
  ```

  and populate the tag message with the release notes

- push the tag to github.com

  ```bash
  git push -u origin master --tags
  ```

- [create a release](https://github.com/gwpy/pyomicron/releases/new) on
  github.com and copy the release notes into the description

- publish the release on pypi.python.org:

  ```bash
  python setup.py sdist bdist_wheel --universal
  python -m twine upload dist/pyomicron-X.Y.Z*
  ```
