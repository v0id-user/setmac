#!/usr/bin/env bash
# Imports the release signing subkey in CI so git signs release commits and tags.
# Needs RELEASE_GPG_PRIVATE_KEY (armored, from `gpg --export-secret-subkeys <subkey>!`)
# and RELEASE_GPG_PASSPHRASE, both secrets of the `release` environment.
# Commits are made as RELEASE_GIT_EMAIL, which must be a verified email on the
# GitHub account that holds the public key, or GitHub will not mark them Verified.
set -euo pipefail

: "${RELEASE_GPG_PRIVATE_KEY:?RELEASE_GPG_PRIVATE_KEY is not set (release environment secret)}"
: "${RELEASE_GPG_PASSPHRASE:?RELEASE_GPG_PASSPHRASE is not set (release environment secret)}"
RELEASE_GIT_NAME="${RELEASE_GIT_NAME:-semantic-release}"
RELEASE_GIT_EMAIL="${RELEASE_GIT_EMAIL:-hey@v0id.me}"

export GNUPGHOME="${GNUPGHOME:-$HOME/.gnupg}"
mkdir -p "$GNUPGHOME"
chmod 700 "$GNUPGHOME"
# Signing runs without a terminal: the passphrase is preset in the agent instead.
echo "allow-preset-passphrase" >> "$GNUPGHOME/gpg-agent.conf"
gpgconf --kill gpg-agent

printf '%s\n' "$RELEASE_GPG_PRIVATE_KEY" | gpg --batch --quiet --import

# The newest signing-capable subkey with a secret part: its fingerprint and keygrip.
read -r subkey keygrip < <(
    gpg --batch --with-colons --with-keygrip --list-secret-keys |
        awk -F: '$1 == "sec" { signing = 0 }
                 $1 == "ssb" { signing = ($12 ~ /s/) }
                 $1 == "fpr" && signing { fpr = $10 }
                 $1 == "grp" && signing && fpr { print fpr, $10; fpr = "" }' |
        tail -1
) || true
if [ -z "${subkey:-}" ]; then
    echo "Error: RELEASE_GPG_PRIVATE_KEY holds no signing subkey." >&2
    exit 1
fi

gpgconf --launch gpg-agent
"$(gpgconf --list-dirs libexecdir)/gpg-preset-passphrase" --preset "$keygrip" <<< "$RELEASE_GPG_PASSPHRASE"

git config --global user.name "$RELEASE_GIT_NAME"
git config --global user.email "$RELEASE_GIT_EMAIL"
git config --global user.signingkey "${subkey}!"
git config --global gpg.program "$(command -v gpg)"
git config --global commit.gpgsign true
git config --global tag.gpgsign true

# Fail now, not halfway through a release, if signing does not work.
check=$(mktemp -d)
git -C "$check" init --quiet
git -C "$check" commit --quiet --allow-empty -m "signing check"
git -C "$check" verify-commit HEAD 2>/dev/null
rm -rf "$check"

echo "Release commits and tags will be signed with subkey ${subkey: -16} as $RELEASE_GIT_NAME <$RELEASE_GIT_EMAIL>"
