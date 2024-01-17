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

## Install Dependencies

Download the required Python dependencies:

```bash
# (optional) create a new virtual environment
python -m pip venv .venv
source .venv/bin/activate
# install dependencies
python -m pip install -r requirements.txt
```

## Run Demo

You can run the scripted demo with commentary using the run-demo script.

```bash
python run-demo.py
```

## Manual

If you prefer to run the demo manually, follow the steps outlined below.
You will set up a directory structure as follows:

```
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

mkdir {keys,repo,gpg-dir}  # gpg-dir is optional
chmod 700 gpg-dir
cp -r ${OLDPWD}/keys .

cd repo

# Either, follow these steps to set GPG home and create a new keyring and keys,
# or use existing GPG keys. To do so, make note of their key IDs and skip ahead
# to the git repository creation.
# gittuf supports other key types, such as sigstore-oidc and SSH, but this demo
# focuses on GPG based keys. Note that the scripted demo uses SSH keys that are
# checked into the keys directory.
export GNUPGHOME=../gpg-dir

# For more options see:
# https://www.gnupg.org/documentation/manuals/gnupg-devel/Unattended-GPG-key-generation.html
gpg --batch --gen-key <<EOF
Key-Type: 1
Key-Length: 1024
Subkey-Type: 1
Subkey-Length: 1024
Name-Real: Authorized Developer
Name-Email: gittuf.authorized@example.com
Expire-Date: 0
%no-protection
EOF

gpg --batch --gen-key <<EOF
Key-Type: 1
Key-Length: 1024
Subkey-Type: 1
Subkey-Length: 1024
Name-Real: Unauthorized Developer
Name-Email: gittuf.unauthorized@example.com
Expire-Date: 0
%no-protection
EOF

# Make note of the key IDs for "Authorized Developer" and
# "Unauthorized Developer". The IDs are 40 character long hex strings.
# These will be referred to as <authorized_key> and <unauthorized_key>
# in the followings steps, and need to be filled in manually.
gpg --list-public-keys

# Create demo git repository
git init -b main

git config --local user.signingkey <authorized_key>  # amend config options as needed for your chosen signing mechanism
git config --local user.name gittuf-demo
git config --local user.email gittuf.demo@example.com


gittuf trust init -k ../keys/root

gittuf trust add-policy-key -k ../keys/root --policy-key ../keys/targets.pem

gittuf policy init -k ../keys/targets

# Add branch protection rule
gittuf policy add-rule -k ../keys/targets --rule-name 'protect-main' --rule-pattern git:refs/heads/main --authorize-key gpg:<authorized_key>

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
gittuf policy add-rule -k ../keys/targets --rule-name 'protect-readme' --rule-pattern file:README.md --authorize-key gpg:<authorized_key>

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

## gittuf Verification via GitHub Actions

It is possible to use gittuf in your CI workflows using the
[gittuf-installer GitHub Action](https://github.com/gittuf/gittuf-installer).
For an example of gittuf verification in CI, take a look at
[gittuf/ci-demo](https://github.com/gittuf/ci-demo).
