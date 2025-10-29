Dual-Source Identity, Single Global Gate — Final Requirements (Internet PROD, Sanitised DEV)
Facts we’re designing to


PROD: Internet-facing; almost all users on LAN. Existing cookie session auth stays primary.


DEV: Short-lived envs; data sanitised (desensitise step). No sensitive data.


Goal: auth required is identical in all envs; only identity source can differ (cookie vs bearer).


Config (env flags)


ALLOW_DEV_BEARER: false by default; must be false in PROD.


DEV_JWT_SECRET: only set when ALLOW_DEV_BEARER=true.


DEV_HOST_PATTERNS: substrings that define dev hosts (e.g., .dev-, .localhost).


AUTH_ANON_ALLOWLIST: explicit public prefixes (/login, /logout, /healthz, /static/, /api/public/).


Required behavior


Identity layer (non-blocking)


Keep cookie/session handling unchanged.


If ALLOW_DEV_BEARER=true and host matches DEV_HOST_PATTERNS and Authorization: Bearer … present:


Validate HS256 with DEV_JWT_SECRET, short-lived (~10–15 min), iss=dev.


On success, mark the request authenticated.




On failure: do nothing (remain anon or cookie-auth). No exceptions.




Global gate (blocking, same in all envs)


If not authenticated and path not in AUTH_ANON_ALLOWLIST:


/api/** → 401 JSON.


Everything else → 302 to /login.




Do not rely on per-view decorators for protection; the gate is authoritative.




Environment stance


PROD: ALLOW_DEV_BEARER=false (bearer ignored). Cookies only.


DEV: ALLOW_DEV_BEARER=true on dev hosts; cookies still work.




CORS / CSRF (unchanged)


Cookie flows: existing CSRF stays.


API remains tokenised (unauth → 401).


Dev bearer calls: allow the dev FE origin; no credentials on those calls.




Security posture (right-sized)


PROD basics: Secure + HttpOnly cookies, SameSite=Lax (or None if cross-site FE), TLS/HSTS, modest rate-limit on auth endpoints.


DEV: No special logging controls beyond not dumping raw Authorization by default; sanitised data means low impact.


Must-nots


Do not expand public surface beyond AUTH_ANON_ALLOWLIST.


Do not add env-based CSRF exceptions for cookie flows.


Do not accept bearer in PROD (flag must be off).


Minimal behavioural checks


Anonymous → protected HTML = 302 /login; protected API = 401.


Prod config: bearer on protected API = 401.


Dev config + dev host + valid dev token: protected API succeeds.


Allowlist paths reachable anonymously.


Rollout


Add identity layer + global gate under flags.


Verify in DEV (cookie + bearer), then UAT/PROD (bearer ignored).


Keep desensitise step in DEV as-is; no further hardening needed there.


Future-proofing (optional)


If you later move PROD to bearer, flip precedence in the identity layer; the gate remains unchanged.
