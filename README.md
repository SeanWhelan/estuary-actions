# Estuary GitHub Actions

Reusable composite actions for Estuary Flow:

- Authenticates `flowctl` using a provided token
- Pulls catalog specs by prefix or name

## Actions

### Auth

Path: `.github/actions/auth`

Inputs:

- `token` (required): Estuary refresh token.

Example:

```yaml
- uses: SeanWhelan/estuary-test/.github/actions/auth@v0.1.0
  with:
    token: ${{ secrets.ESTUARY_REFRESH_TOKEN }}
```

### Pull Specs

Path: `.github/actions/pull-specs`

Inputs:

- `prefix` (optional): Catalog prefix, e.g. `sean-estuary/` or `your-org/`.
- `name` (optional): Full catalog name (capture, collection, derivation, or materialization).

Exactly one of `prefix` or `name` must be provided.

Example:

```yaml
- uses: SeanWhelan/estuary-test/.github/actions/pull-specs@v0.1.0
  with:
    prefix: sean-estuary/
```

Or by name:

```yaml
- uses: SeanWhelan/estuary-test/.github/actions/pull-specs@v0.1.0
  with:
    name: acmeCo/marketing/emailList
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
      # Or, pull a single spec by name instead of prefix:
      # - uses: SeanWhelan/estuary-test/.github/actions/pull-specs@v0.1.0
      #   with:
      #     name: acmeCo/marketing/emailList
```

## Notes

- A refresh token is required. Access tokens expire quickly and will cause runs to fail.
- How to obtain your refresh token:
  - In the Estuary UI, navigate to: Admin → CLI-API → Generate token.
  - Copy the refresh token. You’ll only be able to see it once.
- How to set the token as a GitHub secret:
  - In your repository, go to: Settings → Secrets and variables → Actions → New repository secret.
  - Name it `ESTUARY_REFRESH_TOKEN` and paste the token value.
  - Use it in workflows: `token: ${{ secrets.ESTUARY_REFRESH_TOKEN }}`.
- The actions download `flowctl` on each run for Ubuntu runners.
- To consume from a stable ref, use a tag like `v0.1.0`.
