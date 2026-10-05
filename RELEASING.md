# Releasing

Both packages are versioned in lockstep and released from one git tag.

## Version lives in four places

| File | Field |
| --- | --- |
| `python/pyproject.toml` | `version = "…"` |
| `python/src/laya_mlx_http/__init__.py` | `__version__ = "…"` |
| `ai-provider/package.json` | `"version"` |
| `ai-provider/src/version.ts` | `VERSION` |

```bash
python3 scripts/versions.py set 0.2.0   # or: make bump VERSION=0.2.0
python3 scripts/versions.py check       # or: make check-versions (CI runs this)
```

## One-time setup

### PyPI — `laya-mlx-http`

1. Sign in to [pypi.org](https://pypi.org) → Account → **Publishing** →
   **Add a pending publisher**:
   - Owner: `noahwaldner`
   - Repository: `laya-mlx-http`
   - Workflow name: `release.yml`
   - Environment: *(leave empty)*
2. No API tokens are needed. The pending publisher creates the project on the
   first release.

### npm — `@noahwaldner/laya-mlx-http`

1. npmjs.com → `@noahwaldner/laya-mlx-http` → Settings → **Trusted Publisher**
   → GitHub Actions: owner `noahwaldner`, repository `laya-mlx-http`,
   workflow `release.yml`.
2. **Allowed actions**: tick `npm publish` (new configurations default to
   stage-only).
3. No tokens are stored in GitHub — CI authenticates via OIDC. Note that
   `npm stage publish` is always allowed for a trusted publisher, so a future
   workflow can stage instead of publish and leave approval to a human.

## Cutting a release

```bash
python3 scripts/versions.py set 0.2.0
git commit -am "bump 0.2.0"
git tag v0.2.0
git push origin master --tags
```

The [Release workflow](.github/workflows/release.yml) verifies that the tag
matches all four version strings, then publishes both packages in parallel.

Verify:

```bash
pip index versions laya-mlx-http
npm view @noahwaldner/laya-mlx-http version
```

## Notes

- **Provenance**: npm generates a provenance attestation automatically when
  publishing via OIDC from a **public** repository. While the repo is private
  the publish still succeeds, it just carries no attestation.
- **Manual fallback** (no CI):

  ```bash
  uv build --out-dir dist python && uv publish dist/*   # PyPI token via UV_PUBLISH_TOKEN
  cd ai-provider && npm publish --access public          # after npm login
  ```

- PyPI and npm do not allow re-uploading an existing version — bump the
  version for every release.
