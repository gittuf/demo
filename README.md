# gittuf/demo

A demo of gittuf.

## Install gittuf

The [gittuf repository](https://github.com/gittuf/gittuf) provides pre-built
binaries that are signed and published using
[GoReleaser](https://goreleaser.com/). The signature for these binaries are
generated using [Sigstore](https://www.sigstore.dev/), using the release
workflow's identity. Please use release v0.1.0 or higher, as prior releases were
created to test the release workflow.  Alternatively, gittuf can also be
installed using `go install`.

To build from source, clone the repository and run `make`. This will also run
the test suite prior to installing gittuf. Note that Go 1.21 or higher is
necessary to build gittuf.

```bash
git clone https://github.com/gittuf/gittuf
cd gittuf
make
```

## Run Demo

You can run the scripted demo with commentary using the run-demo script.

```bash
python run-demo.py
```

## Manual

If you prefer to run the demo manually, set up a directory structure as follows:

```
.
├── keys
└── repo
```

`keys` must be copied from this repository. You must also create two
Git-compatible signing keys, one that is authorized for the demo policy and one
that is not. Finally, set your working directory to `repo`.

```bash
git init -b main

git config --local user.signingkey <authorized_key>  # amend config options as needed for your chosen signing mechanism
git config --local user.name gittuf-demo
git config --local user.email gittuf.demo@example.com

export GNUPGHOME=../gpg-dir  # optional: set GPG home if you're using GPG keys from a non-default keyring

gittuf trust init -k ../keys/root

gittuf trust add-policy-key -k ../keys/root --policy-key ../keys/targets.pub

gittuf policy init -k ../keys/targets

# Add branch protection rule
gittuf policy add-rule -k ../keys/targets --rule-name 'protect-main' --rule-pattern git:refs/heads/main --authorize-key <signing_mechanism>:<authorized_key>

echo 'Hello, world!' > README.md
git add README.md
git commit -m 'Initial commit'

gittuf rsl record main

# This will succeed!
gittuf verify-ref -f main

# Simulate violation by using unauthorized key
git config --local user.signingkey <unauthorized_key>

echo 'This is not allowed!' >> README.md
git add README.md
git commit -m 'Update README.md'

gittuf rsl record main

# This will fail as branch protection rule is violated!
gittuf verify-ref -f main

# Rewind to known good state
git reset --hard HEAD~1
git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1
git config --local user.signingkey <authorized_key>

# Add file protection rule
gittuf policy add-rule -k ../keys/targets --rule-name 'protect-readme' --rule-pattern file:README.md --authorize-key <signing_mechanism>:<authorized_key>

# Make change to README.md using unauthorized key
git config --local user.signingkey <unauthorized_key>

echo 'This is not allowed!' >> README.md
git add README.md
git commit -m 'Update README.md'

# But record RSL entry using authorized key to meet branch protection rule
git config --local user.signingkey <authorized_key>
gittuf rsl record main

# This will fail as file protection rule is violated!
gittuf verify-ref -f main
```
