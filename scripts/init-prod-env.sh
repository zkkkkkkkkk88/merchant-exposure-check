#!/usr/bin/env sh
set -eu
umask 077

output_path="${1:-deploy/.env.production}"
if [ -e "$output_path" ]; then
    echo "$output_path already exists; refusing to overwrite it." >&2
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
postgres_password="$(openssl rand -hex 24)"
access_session_secret="$(openssl rand -hex 32)"
internal_api_secret="$(openssl rand -hex 32)"

printf "Doubao ARK API key (leave empty to configure later): "
stty -echo
trap 'stty echo' EXIT INT TERM
read -r ark_api_key
stty echo
trap - EXIT INT TERM
printf "\n"

{
    printf "POSTGRES_DB=exposure\n"
    printf "POSTGRES_USER=exposure\n"
    printf "POSTGRES_PASSWORD=%s\n" "$postgres_password"
    printf "ARK_API_KEY=%s\n" "$ark_api_key"
    printf "ARK_MODEL=doubao-seed-2-0-lite-260215\n"
    printf "AMAP_KEY=\n"
    printf "TENCENT_MAP_KEY=\n"
    printf "ACCESS_AUTH_REQUIRED=true\n"
    printf "ACCESS_ADMIN_USERNAME=admin\n"
    printf "ACCESS_ADMIN_PASSWORD_HASH='%s'\n" "$admin_hash"
    printf "ACCESS_DEMO_USERNAME=demo\n"
    printf "ACCESS_DEMO_PASSWORD_HASH='%s'\n" "$demo_hash"
    printf "ACCESS_SESSION_SECRET=%s\n" "$access_session_secret"
    printf "INTERNAL_API_SECRET=%s\n" "$internal_api_secret"
} > "$output_path"
chmod 600 "$output_path"
echo "Created $output_path with permissions 600."
