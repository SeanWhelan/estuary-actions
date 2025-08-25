# Estuary GitHub Actions

Reusable composite actions for Estuary Flow:

- Authenticates `flowctl` using a provided token
- Pulls catalog specs by prefix or name
- Toggles a task's `shards.disable` by catalog name (optionally publish)
- Fetches live status for items and exposes outputs for alerting
- Publishes specs from a top-level `flow.yaml` with safety checks

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

### Toggle Task

Path: `.github/actions/toggle-task`

Inputs:

- `name` (required): Full catalog name (capture, collection, derivation, or materialization).
- `action` (required): `disable` or `enable`.
- `tolerate-test-failure` (optional, default `true`): If `flowctl test` fails (e.g., connector offline), continue.
- `publish` (optional, default `false`): If `true`, publish the changes using the top-level `flow.yaml`.

Behavior:

- Pulls specs for the provided `name` and resolves imports into a temp working directory.
- Locates the full spec mapping and updates or adds `shards.disable`.
- Preserves any existing `shards` settings and moves the `shards` block to the end of the mapping.
- Strips `expectPubId` under the target mapping to allow publishing.
- Runs `flowctl catalog test`; optionally publishes from the top-level `flow.yaml`.

Example (disable):

```yaml
- uses: SeanWhelan/estuary-test/.github/actions/toggle-task@v0.1.0
  with:
    name: sean-estuary/pg-mongo/source-postgres
    action: disable
    tolerate-test-failure: "true"
    publish: "false"
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

## Full workflow example (Toggle Task)

```yaml
name: Toggle Estuary Task
on:
  workflow_dispatch:
    inputs:
      name:
        description: Full catalog name to toggle
        required: true
      action:
        description: disable or enable
        required: true
        default: disable
        type: choice
        options: [disable, enable]
      tolerate_test_failure:
        description: Tolerate flowctl test failures
        required: false
        default: "true"
      publish:
        description: Publish the modified spec
        required: false
        default: "false"
jobs:
  toggle:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: SeanWhelan/estuary-test/.github/actions/auth@v0.1.0
        with:
          token: ${{ secrets.ESTUARY_REFRESH_TOKEN }}
      - uses: SeanWhelan/estuary-test/.github/actions/toggle-task@v0.1.0
        with:
          name: ${{ github.event.inputs.name }}
          action: ${{ github.event.inputs.action }}
          tolerate-test-failure: ${{ github.event.inputs.tolerate_test_failure }}
          publish: ${{ github.event.inputs.publish }}
```

### Publish

Path: `.github/actions/publish`

Inputs:

- `source` (optional, default `flow.yaml`): Path to top-level `flow.yaml`.
- `default-data-plane` (optional): Data plane for created specs.
- `strip-expect-pub-id` (optional, default `true`): Remove `expectPubId:` before publishing.
- `run-test` (optional, default `true`): Run `flowctl catalog test` prior to publish.

Example:

```yaml
- uses: SeanWhelan/estuary-test/.github/actions/publish@v0.1.0
  with:
    source: path/to/flow.yaml
    default-data-plane: ops/dp/public/gcp-us-central1-c2
    strip-expect-pub-id: "true"
    run-test: "true"
```

Workflow example: `.github/workflows/estuary-publish.yml` demonstrates dispatch inputs for these options.

### Status

Path: `.github/actions/status`

Inputs:

- `names` (required): Space-separated catalog names.
- `output-format` (optional, default `json`): `json`, `yaml`, or `table` for logs.

Outputs (when a single name is provided):

- `summary_status`: High-level status, e.g. `ok`.
- `summary_message`: Human-readable status message.
- `spec_type`: `capture`, `collection`, etc.
- `last_pub_id`, `last_build_id`
- `connector_message`: Last connector message, if any.

Example:

```yaml
- uses: SeanWhelan/estuary-test/.github/actions/status@v0.1.0
  id: est
  with:
    names: sean-estuary/pg-mongo/source-postgres
    output-format: json
- name: Alert if not ok
  if: steps.est.outputs.summary_status && steps.est.outputs.summary_status != 'ok'
  run: |
    echo "ALERT: ${ { steps.est.outputs.summary_status } } - ${ { steps.est.outputs.summary_message } }"
```

Workflow example: `.github/workflows/estuary-status.yml` demonstrates usage and a conditional alert step.

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
