# Estuary GitHub Actions (Auth, Pull Specs)

Reusable composite actions for Estuary Flow:
- Authenticates `flowctl` using a provided token
- Pulls catalog specs by prefix

## Actions

### Auth
Path: `.github/actions/auth`

Inputs:
- `token` (required): Estuary token. Prefer a refresh token from the Estuary dashboard (CLI-API tab).

Example:
```yaml
- uses: SeanWhelan/estuary-test/.github/actions/auth@v0.1.0
  with:
    token: ${{ secrets.ESTUARY_REFRESH_TOKEN }}
```

### Pull Specs
Path: `.github/actions/pull-specs`

Inputs:
- `prefix` (required): Catalog prefix, e.g. `sean-estuary/` or `your-org/`.
- `output` (optional): Output file path. Default: `estuary_specs.json`.

Example:
```yaml
- uses: SeanWhelan/estuary-test/.github/actions/pull-specs@v0.1.0
  with:
    prefix: sean-estuary/
    output: estuary_specs.json
```

## Full workflow example
```yaml
name: Pull Estuary Specs
on:
  workflow_dispatch:
jobs:
  pull:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: SeanWhelan/estuary-test/.github/actions/auth@v0.1.0
        with:
          token: ${{ secrets.ESTUARY_REFRESH_TOKEN }}
      - uses: SeanWhelan/estuary-test/.github/actions/pull-specs@v0.1.0
        with:
          prefix: sean-estuary/
          output: estuary_specs.json
      - uses: actions/upload-artifact@v4
        with:
          name: estuary-specs
          path: estuary_specs.json
```

## Notes
- Provide your own token via `with: token: ${{ secrets.YOUR_TOKEN }}`. A refresh token is recommended so runs don’t fail after 1 hour.
- The actions download `flowctl` on each run for Ubuntu runners.
- To consume from a stable ref, use a tag like `v0.1.0`.
