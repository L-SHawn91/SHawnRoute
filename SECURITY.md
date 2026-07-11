# Security Policy

## Supported versions

SHawnRoute is pre-release. Security fixes apply to the latest main branch until the first stable release.

## Credential policy

SHawnRoute must never read, copy, print, upload, or persist OAuth tokens, API-key values, browser cookies, or provider credential files. Adapters should query official runtime status surfaces and return classified metadata only.

## Reporting a vulnerability

Do not open a public issue containing credentials, personal paths, or exploit details. Contact the maintainer privately through the security contact published in the GitHub repository profile. Include affected version, reproduction steps using fake credentials, and expected impact.

## Non-goals

SHawnRoute does not pool accounts, bypass provider limits, resell subscription access, or expose a user's personal subscription as a shared API.

## Release gate

A release is blocked if tests or the public safety scanner detect credential-shaped content, private absolute paths, nondeterministic planning, or unexpected writes during read-only commands.
