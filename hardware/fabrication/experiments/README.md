# Hardware history and experiments

The [candidate index](INDEX.md) lists retained searches, rejected alternatives
and earlier checkpoints separately from the [current two-board designs](../active/README.md).
An unselected candidate may still be an input to a current audit; unselected
does not mean disposable or independently validated.

The original files stay under `staging/`. Existing reviews bind their paths and
bytes, including rejected cases used to demonstrate regressions. Follow the
owning README and source-hash manifests when reproducing an experiment.

Regenerate or check the navigation catalog from the repository root:

```sh
uv run --locked python -m tools.artifacts.catalog_hardware
uv run --locked python -m tools.artifacts.catalog_hardware --check
```

The catalog inventories tracked files, including staged candidates. New untracked work stays outside this saved index.
It records selection and file sizes, without running native DRC, rerouting a
board or granting fabrication approval.
