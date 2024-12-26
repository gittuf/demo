!/usr/bin/env bash
# ^ or #!/bin/bash depending on your environment

# Exit immediately if a command exits with a non-zero status
set -e

# ---------------------------------------------------------
# Step 1: Setup keys folder and generate ECDSA SSH keys
# ---------------------------------------------------------
echo "Creating 'keys' directory and generating SSH keys..."
mkdir -p keys
cd keys

ssh-keygen -q -t ecdsa -N "" -f R1
ssh-keygen -q -t ecdsa -N "" -f R2
ssh-keygen -q -t ecdsa -N "" -f R3

# ---------------------------------------------------------
# Step 2: Initial repository setup
# ---------------------------------------------------------
echo "Setting up initial Git repository in 'repo' directory..."
cd ..
mkdir -p repo
cd repo

git init -q -b main
git config --local gpg.format ssh
git config --local user.signingkey ../keys/R1

# ---------------------------------------------------------
# Step 3: Set up Roots of Trust 
# ---------------------------------------------------------
echo "Configuring roots of trust..."

gittuf trust init -k ../keys/R1
gittuf trust add-root-key -k ../keys/R1 --root-key ../keys/R2
gittuf trust add-root-key -k ../keys/R1 --root-key ../keys/R3
gittuf trust update-root-threshold -k ../keys/R1 --threshold 2

git config --local user.signingkey ../keys/R2
gittuf trust sign -k ../keys/R2

git config --local user.signingkey ../keys/R3
gittuf trust sign -k ../keys/R3

git config --local user.signingkey ../keys/R1
gittuf trust apply

# ---------------------------------------------------------
# Step 3: Set up Policy Keys 
# ---------------------------------------------------------
echo "Configuring policy keys..."

cd ../keys
ssh-keygen -q -t ecdsa -N "" -f P1
ssh-keygen -q -t ecdsa -N "" -f P2
ssh-keygen -q -t ecdsa -N "" -f P3

cd ../repo
gittuf trust add-policy-key -k ../keys/R1 --policy-key ../keys/P1
gittuf trust add-policy-key -k ../keys/R1 --policy-key ../keys/P2
gittuf trust add-policy-key -k ../keys/R1 --policy-key ../keys/P3

gittuf trust update-policy-threshold -k ../keys/R1 --threshold 2   

git config --local user.signingkey ../keys/R2
gittuf trust sign -k ../keys/R2

git config --local user.signingkey ../keys/R3
gittuf trust sign -k ../keys/R3

gittuf trust apply

# ---------------------------------------------------------
# Step 4: Set up Rules 
# ---------------------------------------------------------
echo "Configuring rules..."

#Additional Git Setup
echo "Hello, world!" > README.md
mkdir src 
mkdir ios  
mkdir android 

git add . 
git commit -q -S -m "Initial commit"  
git branch -q prod 

#Setup Additional Keys 
cd ../keys
ssh-keygen -q -t ecdsa -N "" -f Alice 
ssh-keygen -q -t ecdsa -N "" -f Bob 
ssh-keygen -q -t ecdsa -N "" -f Carol 
ssh-keygen -q -t ecdsa -N "" -f Helen 
ssh-keygen -q -t ecdsa -N "" -f Ilda  

#Setup Policy 
cd ../repo
git config --local user.signingkey ../keys/P1
gittuf policy init -k ../keys/P1 --policy-name targets

gittuf policy add-key -k ../keys/P1 --public-key ../keys/Alice.pub
gittuf policy add-key -k ../keys/P1 --public-key ../keys/Bob.pub
gittuf policy add-key -k ../keys/P1 --public-key ../keys/Carol.pub
gittuf policy add-key -k ../keys/P1 --public-key ../keys/Helen.pub
gittuf policy add-key -k ../keys/P1 --public-key ../keys/Ilda.pub

#Setup Rules 
chmod 0600 ../keys/*
gittuf policy add-rule -k ../keys/P1 \
--rule-name protect-main-prod \
--rule-pattern git:refs/heads/main \
--rule-pattern git:refs/heads/prod \
--authorize-key ../keys/Alice.pub \
--authorize-key ../keys/Bob.pub \
--authorize-key ../keys/Carol.pub \
--threshold 2 

gittuf policy add-rule -k ../keys/P1 \
--rule-name protect-ios-app \
--rule-pattern file:ios/* \
--authorize-key ../keys/Alice.pub 

gittuf policy add-rule -k ../keys/P1 \
--rule-name protect-android-app \
--rule-pattern file:android/* \
--authorize-key ../keys/Bob.pub 

gittuf policy add-rule -k ../keys/P1 \
--rule-name protect-core-libraries \
--rule-pattern file:src/* \
--authorize-key ../keys/Carol.pub \
--authorize-key ../keys/Helen.pub \
--authorize-key ../keys/Ilda.pub \
--threshold 2 

git config --local user.signingkey ../keys/P1
gittuf policy sign -k ../keys/P1 --policy-name targets

git config --local user.signingkey ../keys/P2
gittuf policy sign -k ../keys/P2 --policy-name targets

gittuf policy apply

# ---------------------------------------------------------
# Step 5: Set up Delagations 
# ---------------------------------------------------------
echo "Configuring delagations..."

cd ../keys 
ssh-keygen -q -t ecdsa -N "" -f Dana 
ssh-keygen -q -t ecdsa -N "" -f George 
ssh-keygen -q -t ecdsa -N "" -f Eric  
ssh-keygen -q -t ecdsa -N "" -f Frank 

cd ../repo
chmod 0600 ../keys/*

# Delagate protect-ios-app
git config --local user.signingkey ../keys/P3
gittuf policy init -k ../keys/P3 --policy-name protect-ios-app

git config --local user.signingkey ../keys/Alice
gittuf policy add-key -k ../keys/Alice \
--policy-name protect-ios-app \
--public-key ../keys/Dana.pub \
--public-key ../keys/George.pub
gittuf policy add-rule -k ../keys/Alice \
--policy-name protect-ios-app \
--rule-name authorize-ios-team \
--rule-pattern file:ios/* \
--authorize-key ../keys/Dana.pub \
--authorize-key ../keys/George.pub \
--threshold 1 

gittuf policy sign -k ../keys/Alice --policy-name protect-ios-app 
gittuf policy apply 


# Delagate protect-ios-app
git config --local user.signingkey ../keys/P3
gittuf policy init -k ../keys/P3 --policy-name protect-android-app

git config --local user.signingkey ../keys/Bob
gittuf policy add-key -k ../keys/Bob \
--policy-name protect-android-app \
--public-key ../keys/Eric.pub \
--public-key ../keys/Frank.pub

gittuf policy add-rule -k ../keys/Bob \
--policy-name protect-android-app \
--rule-name authorize-android-team \
--rule-pattern file:ios/* \
--authorize-key ../keys/Eric.pub \
--authorize-key ../keys/Frank.pub \
--threshold 1 

gittuf policy sign -k ../keys/Bob --policy-name protect-android-app 
gittuf policy apply 

echo "Done!"