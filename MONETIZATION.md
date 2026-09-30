# Sustainable Postroom

Postroom's strongest position is a private, offline-first developer inbox. Keep the core SMTP capture, local previews, and exports free. Charge for work that benefits teams or requires hosted infrastructure, rather than making a local debugging workflow paywalled.

## Recommended path

1. **Open source + sponsorship now.** The in-app **Contribute** control opens the project page. Configure a sponsor/donation URL at build time when one is available:

   ```sh
   go build -ldflags "-X main.contributeURL=https://github.com/sponsors/YOUR_ACCOUNT"
   ```

   Publish a GitHub Sponsors, Open Collective, or Buy Me a Coffee link alongside a short statement that local capture remains free.

2. **Postroom Team (paid).** Add an optional shared, hosted inbox for staging and QA: workspace access, retention, roles, audit logs, SSO/SAML, and secure share links. This is a clear team value proposition and carries real operating costs.

3. **Postroom CI (usage-based).** Provide a container/headless mode and authenticated HTTP API for tests to wait for, query, and assert captured mail. Bill by retained messages, inboxes, or CI runs—not by individual developers.

4. **Delivery confidence add-on.** Offer opt-in hosted checks: link health with SSRF protections, SpamAssassin or equivalent scoring, HTML/client compatibility reports, and screenshots from real mail clients. These are valuable because they need maintained infrastructure and should not run silently from a local inbox.

## Build next, in order

- Headless/Docker mode plus REST API and test helpers (Playwright, Cypress, Jest, pytest).
- Persistent named inboxes, message tags, retention settings, and search across runs.
- Configurable SMTP fault simulation (delays, temporary failures, recipient rejection) for resilience tests.
- Team workspaces and CI authentication.
- Hosted deliverability and client-rendering checks.

## Guardrails

- Keep all current local features free and functional without an account.
- Make any networked analysis explicitly opt-in, show its destination, and block private-network requests by default.
- Do not sell captured email contents or use them to train models. Email sandboxes often contain secrets and reset links.
