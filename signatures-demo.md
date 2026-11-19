# Signature Verification Demo

This demo shows which signatures gittuf checks when it verifies a change, and
which ones it ignores. It adds branch and file rules, signs commits, RSL
entries, and approvals, and shows the verification result for each case. See
[gittuf/demo#84](https://github.com/gittuf/demo/issues/84).

The demo has 3 scenarios. Each scenario creates its own repository.

## Run Demo

You need `git`, `gittuf`, and `ssh-keygen`.

To run the demo with commentary:

```bash
python3 run-signatures-demo.py
```

To run it without pausing between steps:

```bash
python3 run-signatures-demo.py --no-prompt
```

## What gittuf Checks

For which signatures gittuf checks for each type of rule, see the
[gittuf documentation](https://gittuf.dev/documentation/consumers/verifying).

## Scenarios

| # | Topic | Scenario demonstrated |
|---|---|---|
| 1 | Branch rules | A branch rule checks who signed the RSL entry. A commit signed by Mallory, or not signed at all, passes. An RSL entry signed by Mallory fails. |
| 2 | File rules | A file rule checks the signature of each commit, only for the paths it changes. A path with no file rule accepts any commit. A commit that changes two protected paths needs a signer trusted for both. |
| 3 | Approvals | With 2 of 3 required, one signature is not enough. An approval from someone outside the rule does not count, and signing the same approval twice counts once. An approval goes stale when the feature branch changes. A person who approves and also signs the RSL entry counts once. |

