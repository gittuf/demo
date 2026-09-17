# Recovery Workflow Demo

This demo shows how gittuf detects an unauthorized change to a repository,
how that compromise is surfaced to a developer who clones/pulls the affected
branch, and how anyone with push access can run gittuf's recovery workflow to
repair the branch back to its last known good state, after which the
developer's own clone can safely sync to the fix.

gittuf's recovery workflow does not rewind refs, since that would force
anyone who already pulled the bad state to reset their local history. Instead
it skips (revokes) the RSL entry for the problematic commit, and records a
new "fix" entry pointing to a commit that reverts the tree back to the last
known good state. This way, everyone, including clients that already pulled
the bad commit, can simply fast-forward to the fix. See the [gittuf recovery
documentation](https://github.com/gittuf/gittuf/blob/main/docs/development/gittuf-recovery.md)
for more details on this workflow.

Notably, the fix entry doesn't need to be issued by anyone in particular:
because the revert commit's tree is identical to the last known-good state,
anyone who can push to the repository can issue it, even using an
unauthorized key, as this demo shows.

## Run Demo

You can run the scripted demo with commentary using the run-recovery-demo
script:

```bash
python run-recovery-demo.py
```

## Manual

If you prefer to run the demo manually, follow the steps outlined below. As
with the [basic functionality demo](/demo.md), you will set up a `keys` and
`repo` directory, using the same demo signing keys:

```bash
# Temporary playground
cd $(mktemp -d)

mkdir {keys,repo}
cp -r ${OLDPWD}/keys .

# ssh-keygen requires that key files have proper permissions
chmod 0600 keys/*

cd repo

# Create demo git repository
git init -b main

git config --local gpg.format ssh
git config --local commit.gpgsign true
git config --local user.signingkey ../keys/authorized
git config --local user.name gittuf-demo
git config --local user.email gittuf.demo@example.com

gittuf trust init -k ../keys/root
gittuf trust add-policy-key -k ../keys/root --policy-key ../keys/targets.pub
gittuf policy init -k ../keys/targets

# Add trusted person to gittuf policy file and protect main
gittuf policy add-person -k ../keys/targets --person-ID 'authorized-user' --public-key ../keys/authorized.pub
gittuf policy add-rule -k ../keys/targets --rule-name 'protect-main' --rule-pattern git:refs/heads/main --authorize authorized-user

gittuf policy stage --local-only
gittuf policy apply --local-only

echo 'Hello, world!' > README.md
git add README.md
git commit -m 'Initial commit'

gittuf rsl record main --local-only

# This will succeed!
gittuf verify-ref main
```

### Simulating a compromise

Now simulate an attacker (or a misconfigured automation) pushing a commit to
`main` that was never approved by an authorized person:

```bash
# Switch to a key that isn't authorized by policy
git config --local user.signingkey ../keys/unauthorized

echo 'This change was never approved!' >> README.md
git add README.md
git commit -m 'Malicious update'

gittuf rsl record main --local-only

# This will fail: the branch protection rule was violated!
gittuf verify-ref main
```

Note the hash of the RSL entry for this bad commit; you'll need it below to
skip it. You can print it with:

```bash
git show --pretty=%H refs/gittuf/reference-state-log
```

### A developer pulls the compromised branch

A teammate who isn't aware of the compromise clones the repository. Because
gittuf verifies as part of `gittuf clone`, the compromise is surfaced
immediately, right when they try to pull the branch down, rather than
silently:

```bash
cd ..
gittuf clone repo victim
```

`gittuf clone` reports the same verification failure seen above, even though
the underlying `git clone` succeeds and the malicious commit is now present
in the developer's local copy too.

### Running the recovery workflow

Back in the canonical repository, `main` is repaired by:

1. Skipping the RSL entry for the malicious commit with `gittuf rsl
   annotate --skip`, using the entry hash noted above.
2. Reverting the malicious commit with a new, forward-only commit, and
   recording it in the RSL.

Since the revert commit's tree is identical to the last known-good state,
this fix doesn't require an authorized signer: anyone who can push to the
repository can issue it. To demonstrate this, we'll continue using the same
unauthorized key here:

```bash
cd ../repo

# Skip the RSL entry for the malicious commit
gittuf rsl annotate --skip --local-only --message "Reverting unauthorized change" <bad-entry-hash>

# Anyone, even with the unauthorized key, can issue the fix, since the
# revert commit's tree is tree-same as the last known-good state
git revert --no-edit HEAD

gittuf rsl record main --local-only

# This succeeds again!
gittuf verify-ref main
```

### The developer's clone recovers too

The developer who pulled the compromised branch doesn't need to re-clone or
reset any history by force. Because the fix is a new commit on top of the bad
one rather than a rewind, a plain pull and sync fast-forwards them straight to
the recovered state:

```bash
cd ../victim

git pull origin main
gittuf sync origin

# This succeeds!
gittuf verify-ref main
```
