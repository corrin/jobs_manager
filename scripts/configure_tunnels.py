#!/usr/bin/env python3
"""
Configure frontend and backend tunnel URLs in .env file.

Usage:
    python scripts/configure_tunnels.py --backend https://msm-corrin.loca.lt --frontend https://msm-corrin-frontend.loca.lt
    python scripts/configure_tunnels.py --backend https://msm-workflow.ngrok-free.app --frontend https://msm-workflow-front.ngrok-free.app
"""

import argparse
from pathlib import Path
from urllib.parse import urlparse


def extract_hostname(url: str) -> str:
    """Extract hostname from URL."""
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")
    return parsed.netloc


def determine_cookie_domain(backend_url: str) -> str:
    """
    Determine appropriate cookie domain from backend URL.

    Simply removes the first subdomain part from the hostname.

    Examples:
      - foo.loca.lt -> .loca.lt
      - bar.ngrok-free.app -> .ngrok-free.app
      - baz.example.com -> .example.com
    """
    backend_host = extract_hostname(backend_url)
    parts = backend_host.split(".")

    if len(parts) < 2:
        raise ValueError(f"Invalid hostname: {backend_host}")

    # Remove first part, keep the rest
    return "." + ".".join(parts[1:])


# Backend .env update rules
# Key format: variable_name -> value
# Value types:
#   - string: replace value entirely
#   - list: add items to comma-separated list
#   - None: remove this variable
#   - callable: function(backend_url, frontend_url) -> value
BACKEND_UPDATE_RULES = {
    "DJANGO_SITE_DOMAIN": lambda b, f: extract_hostname(b),
    "TUNNEL_URL": lambda b, f: b,
    "TUNNEL_FRONTEND_URL": None,  # Obsolete - remove it
    "NGROK_DOMAIN": lambda b, f: f,
    "ALLOWED_HOSTS": lambda b, f: [extract_hostname(b), extract_hostname(f)],
    "XERO_REDIRECT_URI": lambda b, f: f"{b}/api/xero/oauth/callback/",
    "APP_DOMAIN": lambda b, f: extract_hostname(b),
    "CORS_ALLOWED_ORIGINS": lambda b, f: [
        b,
        f,
        b.replace("https://", "http://"),
        f.replace("https://", "http://"),
    ],
    "CSRF_TRUSTED_ORIGINS": lambda b, f: [
        b,
        f,
        b.replace("https://", "http://"),
        f.replace("https://", "http://"),
    ],
    "FRONT_END_URL": lambda b, f: f,
    "AUTH_COOKIE_DOMAIN": lambda b, f: determine_cookie_domain(b),
}

# Frontend .env update rules
FRONTEND_UPDATE_RULES = {
    "VITE_API_BASE_URL": lambda b, f: b,
    "VITE_ALLOWED_HOSTS": lambda b, f: [extract_hostname(b), extract_hostname(f)],
}


def add_to_list(existing_value: str, new_item: str) -> str:
    """Add item to comma-separated list if not already present."""
    items = [item.strip() for item in existing_value.split(",") if item.strip()]
    if new_item not in items:
        items.append(new_item)
    return ",".join(items)


def check_for_untouched_tunnels(env_path: Path, update_rules: dict) -> None:
    """Warn about tunnel URLs/hosts in .env that aren't covered by update rules."""
    content = env_path.read_text()
    lines = content.split("\n")

    # Patterns that indicate tunnel URLs
    tunnel_patterns = [".loca.lt", ".ngrok", "ngrok-free.app"]

    for i, line in enumerate(lines, 1):
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith("#"):
            continue

        # Parse key=value
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()

        # Skip if this key is already in update rules
        if key in update_rules:
            continue

        # Check if value contains tunnel patterns
        for pattern in tunnel_patterns:
            if pattern in value:
                print(f"Warning: Line {i} has tunnel URL but key '{key}' not in update rules:")
                print(f"  {line}")
                break


def apply_update_rules(
    env_path: Path, update_rules: dict, backend_url: str, frontend_url: str
) -> set:
    """
    Apply update rules to an .env file.

    Returns set of updated variable names.
    """
    if not env_path.exists():
        raise FileNotFoundError(f".env file not found at {env_path}")

    # Read current .env content
    content = env_path.read_text()
    lines = content.split("\n")

    # Track which variables we've updated
    updated = set()

    # Process each line
    new_lines = []
    for line in lines:
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith("#"):
            new_lines.append(line)
            continue

        # Parse key=value
        if "=" not in line:
            new_lines.append(line)
            continue

        key, value = line.split("=", 1)
        key = key.strip()

        # Check if this key needs updating
        if key in update_rules:
            rule = update_rules[key]

            if rule is None:
                # Skip this key (remove it)
                updated.add(key)
                continue

            # Evaluate rule if it's a callable
            if callable(rule):
                rule = rule(backend_url, frontend_url)

            if isinstance(rule, list):
                # Add items to comma-separated list
                new_value = value
                for item in rule:
                    new_value = add_to_list(new_value, item)
                new_lines.append(f"{key}={new_value}")
                updated.add(key)
            else:
                # Replace with new value
                new_lines.append(f"{key}={rule}")
                updated.add(key)
        else:
            # Keep line unchanged
            new_lines.append(line)

    # Write back to file
    env_path.write_text("\n".join(new_lines))

    return updated


def update_backend_env(backend_url: str, frontend_url: str, env_path: Path) -> None:
    """Update backend .env file with tunnel URLs."""
    check_for_untouched_tunnels(env_path, BACKEND_UPDATE_RULES)
    updated = apply_update_rules(env_path, BACKEND_UPDATE_RULES, backend_url, frontend_url)

    print(f"Updated {len(updated)} variables in backend .env:")
    for key in sorted(updated):
        print(f"  - {key}")
    cookie_domain = determine_cookie_domain(backend_url)
    print(f"Cookie domain set to: {cookie_domain}")


def update_frontend_env(backend_url: str, frontend_url: str, env_path: Path) -> None:
    """Update frontend .env file with tunnel URLs."""
    check_for_untouched_tunnels(env_path, FRONTEND_UPDATE_RULES)
    updated = apply_update_rules(env_path, FRONTEND_UPDATE_RULES, backend_url, frontend_url)

    print(f"Updated {len(updated)} variables in frontend .env:")
    for key in sorted(updated):
        print(f"  - {key}")


def update_vite_config(backend_url: str, frontend_url: str, vite_config_path: Path) -> None:
    """Update vite.config.ts allowedHosts array."""
    if not vite_config_path.exists():
        raise FileNotFoundError(f"vite.config.ts not found at {vite_config_path}")

    backend_host = extract_hostname(backend_url)
    frontend_host = extract_hostname(frontend_url)

    content = vite_config_path.read_text()
    lines = content.split("\n")
    new_lines = []

    in_allowed_hosts = False
    skip_until_close_bracket = False

    for line in lines:
        # Found the start of allowedHosts array
        if "const allowedHosts = [" in line:
            in_allowed_hosts = True
            skip_until_close_bracket = True
            # Replace entire array
            new_lines.append("  const allowedHosts = [")
            new_lines.append("    'localhost',")
            new_lines.append(f"    '{backend_host}',")
            new_lines.append(f"    '{frontend_host}',")
            new_lines.append("    ...(env.VITE_ALLOWED_HOSTS ? env.VITE_ALLOWED_HOSTS.split(',').map((host) => host.trim()) : []),")
            new_lines.append("  ]")
            continue

        # Skip lines until we find the closing bracket
        if skip_until_close_bracket:
            if "]" in line and in_allowed_hosts:
                skip_until_close_bracket = False
                in_allowed_hosts = False
            continue

        new_lines.append(line)

    vite_config_path.write_text("\n".join(new_lines))
    print(f"Set vite.config.ts allowedHosts to: localhost, {backend_host}, {frontend_host}")


def main():
    parser = argparse.ArgumentParser(
        description="Configure frontend and backend tunnel URLs in .env files"
    )
    parser.add_argument(
        "--backend",
        required=True,
        help="Backend tunnel URL (e.g., https://msm-corrin.loca.lt)",
    )
    parser.add_argument(
        "--frontend",
        required=True,
        help="Frontend tunnel URL (e.g., https://msm-corrin-frontend.loca.lt)",
    )

    args = parser.parse_args()

    # Validate URLs
    if not args.backend.startswith(("http://", "https://")):
        parser.error("Backend URL must start with http:// or https://")
    if not args.frontend.startswith(("http://", "https://")):
        parser.error("Frontend URL must start with http:// or https://")

    # Hardcoded paths
    script_dir = Path(__file__).parent
    backend_env = script_dir.parent / ".env"
    frontend_dir = script_dir.parent.parent / "jobs_manager_front"
    frontend_env = frontend_dir / ".env"
    vite_config = frontend_dir / "vite.config.ts"

    # Fail early if backend .env doesn't exist
    if not backend_env.exists():
        print(f"Error: Backend .env not found at {backend_env}")
        return 1

    # Fail early if frontend .env doesn't exist
    if not frontend_env.exists():
        print(f"Error: Frontend .env not found at {frontend_env}")
        return 1

    # Fail early if vite.config.ts doesn't exist
    if not vite_config.exists():
        print(f"Error: vite.config.ts not found at {vite_config}")
        return 1

    try:
        # Update backend .env
        print("Updating backend .env...")
        update_backend_env(args.backend, args.frontend, backend_env)

        # Update frontend .env
        print("Updating frontend .env...")
        update_frontend_env(args.backend, args.frontend, frontend_env)

        # Update vite.config.ts
        print("Updating vite.config.ts...")
        update_vite_config(args.backend, args.frontend, vite_config)

        print("Configuration complete!")
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
