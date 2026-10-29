# Test signing key (CI/test builds only)

`omniverse-test.p12` is a **shared test key**, committed on purpose for CI and sideload test
builds. Anyone with this repo can sign as this key, so it is **not** used for GitHub Releases.
(`build_apk.yml` doesn't set `OMNI_KEYSTORE` today, so its artifacts use the debug-key fallback.)

- Alias `omniverse`; store and key password `omniverse-test`. It's PKCS12, valid 30 years.
- To use it, point the `OMNI_KEYSTORE*` env vars at it.
- `versionCode` = 1000 + the workflow run number, so each build is higher than the last.

## Release key (private)

`.github/workflows/release.yml` signs release APKs with a private key kept in GitHub Actions
secrets, never in the repo:

| Secret | What it holds |
| --- | --- |
| `OMNI_RELEASE_KEYSTORE_B64` | base64 of the release PKCS12 keystore |
| `OMNI_RELEASE_KEYSTORE_PASSWORD` | keystore password |
| `OMNI_RELEASE_KEY_ALIAS` | key alias (`omniverse-release`) |
| `OMNI_RELEASE_KEY_PASSWORD` | key password (same as the store password; PKCS12 needs them equal) |

The release job decodes the keystore to `$RUNNER_TEMP`, sets `OMNI_REQUIRE_RELEASE_KEY=1`
(the generated Gradle config then throws instead of falling back to the debug key), and
fails if any secret is missing or the APK isn't signed by `CN=The Omniverse Release`.

The owner keeps a private backup of the keystore and its password. If that key is lost,
updates can no longer install over existing release installs.

**Signature change:** APKs from earlier releases were signed with the test key. Phones that
installed one must uninstall it once before installing a release signed with the new key.
