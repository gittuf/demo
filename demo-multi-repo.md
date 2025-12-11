# Multi-Repository Demo

The multi-repository demo shows how gittuf can manage trust and policies across
multiple repositories. This is useful when you have several related repositories
that need to share security policies or when you want to inherit policies from
authorities (e.g. the OpenSSF).

In this demo, you'll see two repositories working together:

- A **controller repository** that acts as an upstream repository, defining
  policies that can be inherited by other repositories.
- A **network repository** that subscribes to the controller repository and
  inherits its policies.

The demo walks through setting up both repositories, establishing the
relationship between them, and then propagating and verifying changes across the
network. Verification can occur in both repositories, where the downstream
repository can verify that it follows the controller's policies, and where the
controller repository can check for compliance with its policies across
downstream repositories.

## Run Demo

To run the multi-repository demo with commentary, run:

```bash
python run-multi-repo-demo.py
```

The script will automatically set up both repositories in a temporary directory
and guide you through the process with prompts explaining each step.

## Manual Commands

If you prefer to run the demo manually, follow the steps outlined below.

```bash
# Temporary playground
cd $(mktemp -d)

mkdir {keys,controller,repo}
cp -r ${OLDPWD}/keys .

# ssh-keygen requires that key files have proper permissions
chmod 0600 keys/*

cd controller

# Create demo git repository
git init -b main

# Set Git configuration
git config --local gpg.format ssh
git config --local commit.gpgsign true
git config --local user.signingkey ../keys/authorized
git config --local user.name gittuf-demo
git config --local user.email gittuf.demo@example.com

# Initialize gittuf metadata
gittuf trust init -k ../keys/root

# Designate the current repository as a controller
gittuf trust make-controller -k ../keys/root

# (Optional) Designate the downstream repository as one that must inherit this controller's policy
gittuf trust add-network-repository -k ../keys/root --name downstream --location ../repo --initial-root-principal ../keys/root.pub

# Add a global rule that mandates a threshold of at least 1 on every policy rule targeting Git branches
gittuf trust add-global-rule -k ../keys/root --rule-name global-branch-threshold --rule-pattern git:refs/heads/* --type threshold --threshold 1

# Stage and apply gittuf policy
gittuf trust stage -k ../keys/root --local-only
gittuf trust apply -k ../keys/root --local-only

# Switch to the downstream repository
cd ../repo

# Create demo git repository
git init -b main

# Set Git configuration
git config --local gpg.format ssh
git config --local commit.gpgsign true
git config --local user.signingkey ../keys/authorized
git config --local user.name gittuf-demo
git config --local user.email gittuf.demo@example.com

# Initialize gittuf metadata
gittuf trust init -k ../keys/root

# Set the controller repository as an upstream repository
gittuf trust add-controller-repository -k ../keys/root --name controller --location ../controller --initial-root-principal ../keys/root.pub

# Stage and apply gittuf repository
gittuf trust stage -k ../keys/root --local-only
gittuf trust apply -k ../keys/root --local-only

# Propagate/Synchronize the policy from the controller repository
gittuf rsl propagate

# Create a commit on the main branch
echo 'Hello, world!' > README.md
git add README.md
git commit -m 'Initial commit'

gittuf rsl record main --local-only

# This will fail, as there are no trusted signatures defined.
gittuf verify-ref main

# Switch back to the controller repository
cd ../controller

# Verify that the downstream repositories comply with the controller's policy
gittuf verify-network
```
