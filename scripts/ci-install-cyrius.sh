#!/usr/bin/env bash
# ci-install-cyrius.sh — install the Cyrius toolchain pinned in cyrius.cyml, VERIFIED.
#
#     bash scripts/ci-install-cyrius.sh [path/to/cyrius.cyml]
#
# Shared by .github/workflows/ci.yml and release.yml so the two cannot drift.
#
# ⛔ WHAT THIS REPLACES: `curl -sSf .../cyrius/main/scripts/install.sh | CYRIUS_VERSION=... sh`.
# That ran an installer from cyrius's MOVING main branch, unhashed, under a shell without
# pipefail — a 404 handed `sh` an empty stdin and the step went green (measured: curl rc 22,
# step rc 0), and an empty pin made install.sh resolve releases/latest.
#
# Now:
#   1. the pin is read from [package] only, and anything but x.y.z fails the job;
#   2. install.sh comes from the pin's TAG ref and must match a sha256 COMMITTED below;
#   3. the release tarball must match a sha256 COMMITTED below;
#   4. install.sh runs from the verified file against the verified tarball
#      (CYRIUS_INSTALL_TARBALL), so it fetches neither again.
# ⚠ On the CYRIUS_INSTALL_TARBALL path install.sh does not check the release signature, so the
# committed hashes ARE the integrity guarantee. Bumping the pin means bumping them in the same
# commit — an unknown version fails closed, by design.
set -euo pipefail

manifest="${1:-cyrius.cyml}"
[ -f "$manifest" ] || { echo "ci-install-cyrius: no manifest at '$manifest'" >&2; exit 1; }

# Mirrors cyrius's own reader (whitespace, trailing comment, CRLF tolerated), scoped to [package].
pins="$(sed -n '/^\[package\]/,/^\[/{s/^[[:space:]]*cyrius[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p;}' "$manifest")"
version="${pins%%$'\n'*}"
if ! [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "ci-install-cyrius: bad [package].cyrius pin in $manifest: '$version' (want x.y.z)" >&2
    exit 1
fi

case "$(uname -m)" in
    x86_64 | amd64) arch=x86_64 ;;
    aarch64 | arm64) arch=aarch64 ;;
    *) arch="$(uname -m)" ;;
esac
case "$(uname -s)" in
    Linux) os=linux ;;
    *) os="$(uname -s)" ;;
esac
tarball="cyrius-${version}-${arch}-${os}.tar.gz"

# ── Committed hashes ────────────────────────────────────────────────────────────────────────────
# 6.6.6, measured 2026-09-20 (rekha 0.4.5):
#   install.sh  = raw.githubusercontent.com/MacCracken/cyrius/6.6.6/scripts/install.sh, byte-equal
#                 to `git show 6.6.6:scripts/install.sh` in a local cyrius clone.
#   tarball     = releases/download/6.6.6/<tarball>; equals the published .sha256 sidecar and its
#                 line in SHA256SUMS, whose Ed25519 signature `cyrsign verify` accepted against
#                 keys/cyrius-release.ed25519.pub (adbde6b1…4008).
# 6.6.4 entries are kept so a bisect or a revert to the previous pin still installs.
# ⛔ CVE-44 (fixed in 6.6.6's own installer): through 6.6.5 install.sh staged the tarball and its
# signature inputs at FIXED /tmp names, so a local user could swap them between download and verify.
# This script's CYRIUS_INSTALL_TARBALL path never depended on that staging — it hands install.sh a
# file already verified against a committed hash in a `mktemp -d` — but the fix is another reason
# not to pin below 6.6.6.
installer_sha256() {
    case "$1" in
        6.6.6) echo a468278154c7a77ef17d74277a6ec3402b4213373b383de89ee4803d144cb75a ;;
        6.6.4) echo 4deede3d13651f1d71bd9f0ccd21f4fd71ec1cd99276b3cb22aa5c9acbc9761a ;;
        *) return 1 ;;
    esac
}
tarball_sha256() {
    case "$1" in
        cyrius-6.6.6-x86_64-linux.tar.gz) echo 1866a671924b29b90e3e13333cf613cff55a107390ff5686699e1dc63e593e36 ;;
        cyrius-6.6.6-aarch64-linux.tar.gz) echo f00e13294f0a65d3d32db6bfa210543696dc4c3b466f124aa7866f25d965beec ;;
        cyrius-6.6.4-x86_64-linux.tar.gz) echo c2a540c9adc3c1d6a6096a7ee869b9268ce99a5108ddd644e0be8b1d2d292fab ;;
        *) return 1 ;;
    esac
}

want_installer="$(installer_sha256 "$version")" || {
    echo "ci-install-cyrius: no committed install.sh sha256 for cyrius $version." >&2
    echo "  Bump the hash with the pin: add $version to installer_sha256() in $0." >&2
    exit 1
}
want_tarball="$(tarball_sha256 "$tarball")" || {
    echo "ci-install-cyrius: no committed sha256 for $tarball." >&2
    echo "  Bump the hash with the pin: add it to tarball_sha256() in $0." >&2
    exit 1
}

work="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/cyrius-install.XXXXXX")"
trap 'rm -rf "$work"' EXIT

fetch() { # fetch <url> <dest>
    curl --proto '=https' --proto-redir '=https' --tlsv1.2 -sSfL --retry 3 --retry-delay 2 -o "$2" "$1"
}

verify() { # verify <file> <sha256>
    local got
    got="$(sha256sum "$1")"
    got="${got%% *}"
    if [ "$got" != "$2" ]; then
        echo "ci-install-cyrius: sha256 MISMATCH for $(basename "$1")" >&2
        echo "  want $2" >&2
        echo "  got  $got" >&2
        exit 1
    fi
    echo "verified $(basename "$1")  sha256 $got"
}

echo "Installing Cyrius $version ($arch-$os) from $manifest's pin"
fetch "https://raw.githubusercontent.com/MacCracken/cyrius/${version}/scripts/install.sh" "$work/install.sh"
verify "$work/install.sh" "$want_installer"
fetch "https://github.com/MacCracken/cyrius/releases/download/${version}/${tarball}" "$work/$tarball"
verify "$work/$tarball" "$want_tarball"
# A sidecar next to the local tarball makes install.sh re-check it fail-closed as well.
printf '%s  %s\n' "$want_tarball" "$tarball" > "$work/$tarball.sha256"

# Run from the temp dir: install.sh probes its cwd (programs/dlopen-helper.c), not rekha's tree.
(cd "$work" && CYRIUS_VERSION="$version" CYRIUS_INSTALL_TARBALL="$work/$tarball" sh "$work/install.sh")

home="${CYRIUS_HOME:-$HOME/.cyrius}"
[ -x "$home/bin/cyrius" ] || { echo "ci-install-cyrius: $home/bin/cyrius missing after install" >&2; exit 1; }
active="$(tr -d '[:space:]' < "$home/current")"
[ "$active" = "$version" ] || { echo "ci-install-cyrius: active version '$active' != pin '$version'" >&2; exit 1; }

if [ -n "${GITHUB_PATH:-}" ]; then
    echo "$home/bin" >> "$GITHUB_PATH"
fi
echo "Cyrius $version installed at $home"
