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
the test suite prior to installing gittuf. Note that Go 1.23 or higher is
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

If you prefer to run the demo manually, follow the steps outlined below.
You will set up a directory structure as follows:

```bash
.
├── keys
└── repo
```

Where `keys` will be copied from this repository. You will create two
Git-compatible signing keys, one that is authorized for the demo policy and one
that is not. You will see how policies are created, commit changes and run
`gittuf` to verify, both on the happy and failing path:

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

# In addition to SSH keys, Git and gittuf support using GPG keys.
# To use GPG keys instead of SSH keys, replace paths to keys with
# "gpg:fingerprint" and modify the Git configuration options below.

git config --local gpg.format ssh
git config --local commit.gpgsign true
git config --local user.signingkey ../keys/authorized
git config --local user.name gittuf-demo
git config --local user.email gittuf.demo@example.com

gittuf trust init -k ../keys/root

gittuf trust add-policy-key -k ../keys/root --policy-key ../keys/targets.pub

gittuf policy init -k ../keys/targets

# Add key definition to policy
gittuf policy add-key -k ../keys/targets --public-key ../keys/authorized.pub

# Add branch protection rule
gittuf policy add-rule -k ../keys/targets --rule-name 'protect-main' --rule-pattern git:refs/heads/main --authorize-key ../keys/authorized.pub

# Apply policy
gittuf policy apply

echo 'Hello, world!' > README.md
git add README.md
git commit -m 'Initial commit'

gittuf rsl record main

# This will succeed!
gittuf verify-ref main

# Simulate violation by using unauthorized key
git config --local user.signingkey ../keys/unauthorized

echo 'This is not allowed!' >> README.md
git add README.md
git commit -m 'Update README.md'

gittuf rsl record main

# This will fail as branch protection rule is violated!
gittuf verify-ref main

# Rewind to known good state
git reset --hard HEAD~1
git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1
git config --local user.signingkey ../keys/authorized

# Add file protection rule
gittuf policy add-rule -k ../keys/targets --rule-name 'protect-readme' --rule-pattern file:README.md --authorize-key ../keys/authorized.pub

# Apply policy
gittuf policy apply

# Make change to README.md using unauthorized key
git config --local user.signingkey ../keys/unauthorized

echo 'This is not allowed!' >> README.md
git add README.md
git commit -m 'Update README.md'

# But record RSL entry using authorized key to meet branch protection rule
git config --local user.signingkey ../keys/authorized
gittuf rsl record main

# This will fail as file protection rule is violated!
gittuf verify-ref main
```

## gittuf Verification via GitHub Actions

It is possible to use gittuf in your CI workflows using the
[gittuf-installer GitHub Action](https://github.com/gittuf/gittuf-installer).
For an example of gittuf verification in CI, take a look at
[gittuf/ci-demo](https://github.com/gittuf/ci-demo).
