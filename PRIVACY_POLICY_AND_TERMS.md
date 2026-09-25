# ⚖️ The Omniverse & The KickBack — Terms of Service, Privacy Policy & Compliance Framework
**Last Updated:** September 2026 | **Version:** 2.0.0 (Mainnet Pre-Launch Release)

---

## 1. 🌐 Terms of Service & User Agreement

### 1.1 Acceptance of Terms
By downloading, installing, connecting to, or interacting with **The Omniverse SuperApp**, **The KickBack**, or any associated P2P nodes, smart contracts, or edge services (collectively, the "Platform"), you agree to be bound by these Terms of Service. If you do not agree to these terms, you must not access or use the Platform.

### 1.2 User Eligibility & Age Gating (COPPA Compliance)
* **Strict Age Requirement:** The Platform is strictly restricted to individuals **13 years of age or older**. Persons under 13 are prohibited from creating accounts, hosting nodes, or transmitting data.
* **Parental Consent (13–17):** Minors aged 13 to 17 may only use the Platform under parental or legal guardian supervision.
* **Adult Sub-Enclave Isolation:** Content designated for mature audiences is cryptographically isolated in adult sub-enclaves (`sw_adult_sub_enclave_engine.py`) requiring zero-trust cryptographic age verification.

### 1.3 Human-Only Feed Policy & AI Agent Boundaries
* **Human Feed Prohibition:** The KickBack social feed is strictly enforced as a **Human-Only Feed**. AI agents (including `OmniMind` God-Engine instances) are cryptographically barred from posting to public user feeds.
* **System Exceptions:** System information, maintenance banners, and network status updates emitted by verified system nodes are clearly flagged with `author_type: SYSTEM_ANNOUNCEMENT`.

---

## 2. 🛡️ Privacy Policy, Data Sovereignty & GDPR/CCPA Rights

### 2.1 Decentralized Data Architecture
* **Local Storage First:** All personal data, social posts, chat history, and identity keys reside on your local device in encrypted SQLite Write-Ahead Logging (WAL) databases and RocksDB hot caches.
* **No Centralized Harvesting:** The Platform operates on a serverless P2P mesh network (`The-Omni-Hub`). We do not maintain centralized servers to track, harvest, or sell user browsing history, contacts, or behavioral data.

### 2.2 Privacy-Preserving Friend Matching
* **Blind SHA-256 Hashes:** When importing external contacts, phone numbers and email addresses are hashed locally using salted SHA-256 blind algorithms (`hashlib.sha256("OMNI_SALT:" + contact)`). Raw contact info is never transmitted over the P2P mesh.

### 2.3 User Rights (GDPR & CCPA Compliance)
* **Right to Access & Portability:** Users can export their full local Merkle DAG event history at any time in standard JSON/CSV format.
* **Right to Erasure (Pruning):** Local device state can be wiped instantly. P2P mesh nodes enforce cryptographic event expiry and local state pruning without leaving residual server copies.

---

## 3. 💳 Economic Model, Credits & Utility Disclosures

### 3.1 Off-Chain Shadow Credits (Non-Financial Utility Assets)
* **In-App Utility:** In-app balances ("Credits", "Reward XP", "Badges") are non-financial utility units used exclusively within the Platform for content access, creator gifting, and 3D room overlays.
* **Not Securities or Currency:** Credits do not represent debt, equity, or investment contracts. They carry zero promise of financial returns, appreciation, or passive yield.

### 3.2 App Store Guideline Compliance (Apple 3.1.5 & Google Play)
* **In-App Digital Purchases:** Digital goods, avatar cosmetics, and room overlays consumed on mobile devices adhere strictly to Apple App Store Guideline 3.1.5 and Google Play Commerce policies.
* **Decoupled Blockchain Claims:** On-chain Web3 claims on Polygon are voluntary, lazy-minted, and completely decoupled from standard in-app digital purchases.

### 3.3 Creator Monetization & Revenue Split
* **Transparency:** Live stream gifts and tips apply a **2% platform maintenance fee**, with **98% credited directly to the creator's net balance**.
* **Payout & Anti-Fraud Guards:** Cash-out requests undergo automated velocity and bot audits (`kickback_payout_and_anti_fraud_engine.py`) with a minimum payout threshold of $25.00.

---

## 4. ⚖️ Financial & Regulatory Compliance

### 4.1 KYC/AML & Third-Party Payment Delegation
* **No Un-Custodied Fiat Handling:** The Platform does not act as an un-licensed Money Services Business (MSB). All fiat conversions, credit card processing, and cash-out withdrawals are delegated to fully licensed, regulated payment processors and compliant Web3 on/off-ramps.

### 4.2 Skill-Based Interactive Gaming
* **No Chance-Based Gambling:** Real-time stream trivia, prediction markets, and 9x9 survival maze matches function strictly as **skill-based interactions**. Betting, wagering, or chance-based gambling is strictly prohibited.

### 4.3 Tax Disclosures (IRS 1099 Reporting)
* **Creator Tax Responsibility:** Creators earning income above applicable annual tax thresholds (e.g., $600 USD) are responsible for tax compliance. The Platform tracks accumulated payouts for mandatory tax reporting disclosures.

---

## 5. 📞 Contact & Compliance Office

For legal inquiries, privacy requests, or security audit reports, contact:
* **Compliance Office:** `compliance@theomniverse.network`
* **Security & Vulnerability Disclosures:** `security@theomniverse.network`
