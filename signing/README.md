# Test signing key (sideload only)

`omniverse-test.p12` is a **shared test key**, committed on purpose so every GitHub Release APK
has the same signature. That lets a new release install over the previous one on your phone,
without uninstalling first.

- Alias `omniverse`; store and key password `omniverse-test`. It's PKCS12, valid 30 years.
- It's used by `.github/workflows/release.yml` through the `OMNI_KEYSTORE*` env vars.
- `versionCode` = 1000 + the workflow run number, so each release is higher than the last.

**Before any public or Play Store release:** generate a private key, store it in GitHub Secrets,
and point `OMNI_KEYSTORE` at it. Anyone with this repo can sign as this test key.
