# API Access Controls

## Token-Based Authentication

The API authenticates every request using the OAuth 2.0 Authorization Code flow with PKCE (Proof Key for Code Exchange). PKCE prevents authorization code interception attacks against public clients that cannot securely store a client secret.

## Protecting Endpoints From Unauthorized Use

Beyond the login mechanism itself, every endpoint independently verifies that the caller has been granted the specific permission required for that operation before any data is returned or modified. Requests lacking sufficient privilege are rejected before they reach business logic, and the rejection is recorded for later review. This defense-in-depth approach ensures that a compromised or misconfigured client cannot silently escalate its own access simply by guessing valid resource identifiers.
