# Deployment — Summa Vision

> Status: pre-launch. This document is the auth + DNS setup checklist
> for the first production deployment. Extend as deployment matures.

## Current state (pre-deploy)

- **Frontend** (`frontend-public`): local dev only, not deployed.
- **Backend**: local dev only, not deployed.
- **VPS**: provisioned, not yet serving public traffic.
- **DNS**: `summa.vision` managed by Porkbun; no Cloudflare proxy
  configured.
- **Admin auth**: NOT configured. Deploying without the steps in
  this document will expose `/admin/*` to anyone who knows the URL.
  DO NOT deploy without completing the admin auth setup below.

## Pre-deployment checklist

### 1. DNS migration: Porkbun → Cloudflare

1. Create a free Cloudflare account (if not already).
2. In Cloudflare dashboard: **Websites → Add site → `summa.vision`**.
3. Cloudflare scans existing DNS records. Verify all A, AAAA, CNAME,
   MX, and TXT records match what Porkbun currently has. Add any
   missing.
4. Cloudflare shows two nameservers (e.g.
   `alan.ns.cloudflare.com`, `zara.ns.cloudflare.com`). Keep this
   tab open.
5. In Porkbun dashboard for `summa.vision`: **Nameservers →
   Authoritative nameservers → change to the two Cloudflare
   nameservers** from step 4.
6. Save. Propagation takes 1 minute – 24 hours (usually 10–30
   minutes). Monitor via `dig NS summa.vision`.
7. Once Cloudflare shows the site as "Active", proceed.
8. **Enable orange-cloud proxy** for the A / AAAA records pointing
   to the VPS. This is what puts Cloudflare in front of origin
   traffic.

Registrar stays Porkbun (renewals, transfers, ownership unchanged).
Only the nameservers move.

### 2. VPS firewall: restrict origin to Cloudflare IPs

When the orange-cloud proxy is on, all legitimate traffic arrives
from Cloudflare's IP ranges. Direct IP access from anywhere else
should be blocked to prevent bypass.

1. Get the current Cloudflare IPv4 and IPv6 ranges:
   - https://www.cloudflare.com/ips-v4/
   - https://www.cloudflare.com/ips-v6/
2. Configure VPS firewall (example `ufw`):

   ```bash
   # Default: deny all inbound to the web port.
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow 22/tcp  # SSH — restrict by source IP if possible

   # Allow CF IPv4 ranges on 80/443:
   for ip in $(curl -s https://www.cloudflare.com/ips-v4/); do
     sudo ufw allow from "$ip" to any port 80 proto tcp
     sudo ufw allow from "$ip" to any port 443 proto tcp
   done
   # Same for IPv6
   for ip in $(curl -s https://www.cloudflare.com/ips-v6/); do
     sudo ufw allow from "$ip" to any port 80 proto tcp
     sudo ufw allow from "$ip" to any port 443 proto tcp
   done

   sudo ufw enable
   ```

3. Verify origin cannot be reached without the CF proxy:

   ```bash
   # From any machine, direct IP access should time out or be blocked
   curl -I http://<VPS_IP>:443
   # Via Cloudflare should succeed
   curl -I https://summa.vision
   ```

This is what hides the origin IP from casual probing. If the VPS
IP is ever leaked (logs, mistake, etc.), bypass is still blocked
at the firewall.

### 3. Cloudflare Access: protect `/admin/*`

1. Cloudflare dashboard → **Zero Trust → Access → Applications →
   Add an application → Self-hosted**.
2. Application name: `Summa Vision Admin`.
3. Session duration: `24 hours` (or per preference).
4. Application domain: `summa.vision` path `/admin*`. (Use the path
   matcher if the current CF version supports it. Otherwise use a
   subdomain `admin.summa.vision` and add that hostname too.)
5. Identity providers: select one or more (Google, GitHub, email
   one-time PIN). For solo founder, email OTP is simplest — no
   third-party setup needed.
6. Create a policy:
   - Name: `Admin users`
   - Action: `Allow`
   - Include: `Emails → <your email>` (add more as team grows)
7. Save the application.
8. Verify: visit `https://summa.vision/admin` from an incognito
   window. Cloudflare Access redirect page should appear, asking
   for the email. Completing auth should grant access; wrong email
   should be rejected.

Cloudflare handles the auth entirely at the edge. Next.js sees
requests only after Cloudflare has approved them. No app code is
required for the admin auth.

### 4. Environment variables

Required for production deploy (add to VPS environment):

**Frontend** (`frontend-public/.env.production` or process env):

- `NEXT_PUBLIC_API_URL=https://api.summa.vision` (or wherever
  backend is hosted)
- `NEXT_PUBLIC_TURNSTILE_SITE_KEY=<Cloudflare Turnstile site key>`
- `ADMIN_API_KEY=<randomly generated string, kept server-only>`
- `REVALIDATION_SECRET=<randomly generated string>`

**Backend**:

- All settings documented in `backend/src/core/config.py`, including:
  - `environment=production` (triggers model_validator fail-fast
    for missing secrets)
  - `cdn_base_url=https://cdn.summa.vision` (or actual)
  - `public_site_url=https://summa.vision`
  - `turnstile_secret_key=<Cloudflare Turnstile secret key>` (from
    the same Turnstile site as the frontend site key)
  - `admin_api_key=<matches frontend ADMIN_API_KEY>`
  - `s3_bucket=<bucket name>`
  - plus any other production-required settings

### 5. Verification after deploy

Before announcing the URL publicly:

1. Visit `https://summa.vision` as anonymous user → home loads, no
   auth prompt.
2. Visit `https://summa.vision/admin` as anonymous user → CF Access
   redirect page appears.
3. Complete CF Access auth → admin index loads.
4. Log out of CF Access (delete session cookies or use incognito) →
   refresh admin → redirect to auth page again.
5. Try the partner-with-us form: fill and submit with a valid
   Turnstile challenge → success response. Submit with a manipulated
   token (curl with an invalid `turnstile_token` field) → 403
   response.
6. Visit `https://summa.vision/docs` → 404 (FastAPI docs hidden in
   production per Task 10b). `/redoc` and `/openapi.json` also 404.

## Post-launch: Cloudflare Access audit

CF Access logs every successful and failed auth attempt in the
Zero Trust dashboard. Review monthly for anomalies. When team grows,
add members via the policy's `Emails include` list — no code change.

## Migration path to real SSO (future)

When the team moves beyond email-OTP auth, swap the CF Access
identity provider from "one-time PIN" to Google Workspace, GitHub,
or SAML. Policy stays the same, identity source changes. No app
deploy needed.
