#!/usr/bin/env sh
set -eu
umask 077

env_path="${1:-deploy/.env.production}"
if [ ! -f "$env_path" ]; then
    echo "$env_path does not exist." >&2
    exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
    echo "docker is required." >&2
    exit 1
fi
if ! command -v openssl >/dev/null 2>&1; then
    echo "openssl is required." >&2
    exit 1
fi

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
hash_script="$script_dir/../apps/web/scripts/hash-access-password.mjs"

read_password_hash() {
    label="$1"
    printf "%s password: " "$label" >&2
    stty -echo
    trap 'stty echo' EXIT INT TERM
    read -r password
    stty echo
    trap - EXIT INT TERM
    printf "\n" >&2
    if [ -z "$password" ]; then
        echo "$label password cannot be empty." >&2
        exit 1
    fi

    printf "Confirm %s password: " "$label" >&2
    stty -echo
    trap 'stty echo' EXIT INT TERM
    read -r password_confirm
    stty echo
    trap - EXIT INT TERM
    printf "\n" >&2
    if [ "$password" != "$password_confirm" ]; then
        echo "$label passwords do not match." >&2
        exit 1
    fi
    unset password_confirm

    printf "%s\n" "$password" \
        | docker run --rm -i -v "$hash_script:/hash-access-password.mjs:ro" node:24-alpine \
            node /hash-access-password.mjs
    unset password
}

admin_hash="$(read_password_hash "Administrator")"
demo_hash="$(read_password_hash "Demo")"
access_session_secret="$(openssl rand -hex 32)"
internal_api_secret="$(openssl rand -hex 32)"

backup_path="$env_path.backup.$(date +%Y%m%d%H%M%S)"
temp_path="$(mktemp "${env_path}.tmp.XXXXXX")"
trap 'rm -f "$temp_path"' EXIT INT TERM

cp -p "$env_path" "$backup_path"
grep -vE '^(AUTH_USERNAME|AUTH_PASSWORD_HASH|ACCESS_AUTH_REQUIRED|ACCESS_ADMIN_USERNAME|ACCESS_ADMIN_PASSWORD_HASH|ACCESS_DEMO_USERNAME|ACCESS_DEMO_PASSWORD_HASH|ACCESS_SESSION_SECRET|INTERNAL_API_SECRET)=' "$env_path" > "$temp_path"
{
    printf "ACCESS_AUTH_REQUIRED=true\n"
    printf "ACCESS_ADMIN_USERNAME=admin\n"
    printf "ACCESS_ADMIN_PASSWORD_HASH='%s'\n" "$admin_hash"
    printf "ACCESS_DEMO_USERNAME=demo\n"
    printf "ACCESS_DEMO_PASSWORD_HASH='%s'\n" "$demo_hash"
    printf "ACCESS_SESSION_SECRET=%s\n" "$access_session_secret"
    printf "INTERNAL_API_SECRET=%s\n" "$internal_api_secret"
} >> "$temp_path"

chmod 600 "$temp_path"
mv "$temp_path" "$env_path"
trap - EXIT INT TERM
echo "Updated $env_path. Backup: $backup_path"
