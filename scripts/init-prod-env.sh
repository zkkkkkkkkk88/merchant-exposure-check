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

printf "Shared username [tester]: "
read -r auth_username
auth_username="${auth_username:-tester}"
case "$auth_username" in
    *[!A-Za-z0-9._-]*)
        echo "Shared username may contain only letters, numbers, dot, underscore, and hyphen." >&2
        exit 1
        ;;
esac

printf "Shared password: "
stty -echo
trap 'stty echo' EXIT INT TERM
read -r auth_password
stty echo
trap - EXIT INT TERM
printf "\n"
if [ -z "$auth_password" ]; then
    echo "Shared password cannot be empty." >&2
    exit 1
fi

printf "Confirm shared password: "
stty -echo
trap 'stty echo' EXIT INT TERM
read -r auth_password_confirm
stty echo
trap - EXIT INT TERM
printf "\n"
if [ "$auth_password" != "$auth_password_confirm" ]; then
    echo "Shared passwords do not match." >&2
    exit 1
fi
unset auth_password_confirm

auth_hash="$(
    printf "%s\n" "$auth_password" \
        | docker run --rm -i caddy:2-alpine caddy hash-password --algorithm argon2id
)"
unset auth_password
postgres_password="$(openssl rand -hex 24)"

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
    printf "AUTH_USERNAME=%s\n" "$auth_username"
    printf "AUTH_PASSWORD_HASH='%s'\n" "$auth_hash"
} > "$output_path"
chmod 600 "$output_path"
echo "Created $output_path with permissions 600."
