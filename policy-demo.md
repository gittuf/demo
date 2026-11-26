# Policy Demo

This demo runs 9 scenarios that show how gittuf decides whether a change meets
its policy. Each scenario creates its own repository.

## Run Demo

You need `git`, `gittuf`, `ssh-keygen`, and `gpg`.

To run the demo with commentary:

```bash
python3 run-policy-demo.py
```

To run it without pausing between steps:

```bash
python3 run-policy-demo.py --no-prompt
```


## Scenarios

| # | Topic | Scenario demonstrated |
|---|---|---|
| 1 | SSH and GPG | SSH and GPG signatures count toward the same threshold. |
| 2 | Overlapping file rules | A file can match more than one file rule. Meeting any one of them is enough, even if another one is stricter. A file rule is met by the commit signature or by approvals. The RSL entry signature does not count. |
| 3 | Overlapping file rules, flipped | The same two file rules as scenario 2, with their people swapped. A file that matches only one of the rules must meet that rule. A threshold of 2 can be met by one person signing the commit and another person approving it. |
| 4 | Delegations | A delegated rule file must be signed by the people in the rule that delegates to it. A person trusted by the delegated rule cannot change the rule file. |
| 5 | Global rules | Rules that match the same branch are alternatives, so meeting one is enough. Global rules are always required on top. A `block-force-pushes` global rule catches an amended commit. |
| 6 | Thresholds that can never be met | gittuf rejects a rule whose threshold is 0 or higher than the number of principals in it. A person with two keys still counts once. Global threshold rules are not checked this way, and any principal in the policy counts toward them. |
| 7 | Key reuse | One person’s keys can also be registered as separate key principals. |
| 8 | Policy thresholds | Once the root or policy threshold is 2, every change needs both keys, including the change that raises it. A policy key cannot change the root of trust. |
| 9 | RSL history | `gittuf verify-ref` checks the full history by default, and `--latest-only` checks only the newest entry. A bad entry is recovered by skipping it, skipping every entry built on it, and recording a fix. An older policy recorded in the RSL is detected as a rollback. |