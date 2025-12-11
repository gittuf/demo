# Basic Functionality Demo

This demo covers the basic functionality of gittuf, and simulates creating a
gittuf repository for a repository. Both valid and invalid changes to the
repository are simulated.

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

# Add trusted person to gittuf policy file
gittuf policy add-person -k ../keys/targets --person-ID 'authorized-user' --public-key ../keys/authorized.pub

# Add branch protection rule
gittuf policy add-rule -k ../keys/targets --rule-name 'protect-main' --rule-pattern git:refs/heads/main --authorize authorized-user

# Stage and apply policy
gittuf policy stage --local-only
gittuf policy apply --local-only

echo 'Hello, world!' > README.md
git add README.md
git commit -m 'Initial commit'

gittuf rsl record main --local-only

# This will succeed!
gittuf verify-ref main

# Simulate violation by using unauthorized key
git config --local user.signingkey ../keys/unauthorized

echo 'This is not allowed!' >> README.md
git add README.md
git commit -m 'Update README.md'

gittuf rsl record main --local-only

# This will fail as branch protection rule is violated!
gittuf verify-ref main

# Rewind to known good state
git reset --hard HEAD~1
git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1
git config --local user.signingkey ../keys/authorized

# Add file protection rule
gittuf policy add-rule -k ../keys/targets --rule-name 'protect-readme' --rule-pattern file:README.md --authorize authorized-user

# Stage and apply policy
gittuf policy stage --local-only
gittuf policy apply --local-only

# Make change to README.md using unauthorized key
git config --local user.signingkey ../keys/unauthorized

echo 'This is not allowed!' >> README.md
git add README.md
git commit -m 'Update README.md'

# But record RSL entry using authorized key to meet branch protection rule
git config --local user.signingkey ../keys/authorized
gittuf rsl record main --local-only

# This will fail as file protection rule is violated!
gittuf verify-ref main
```
