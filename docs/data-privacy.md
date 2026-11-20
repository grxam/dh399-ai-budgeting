# Data & privacy policy

Receipts reveal where you live, shop, and what you buy.

1. **Repo contains synthetic data only.** Make fake receipts or heavily redact real ones (names, card digits, addresses, loyalty IDs).
2. **Real data stays local.** `data/*` (except `data/samples/`) and all `*.db` files are git-ignored.
3. **Images are sent to the Anthropic API** for extraction. Only process receipts you're comfortable sharing with that service; check the course/ethics requirements for your project.
4. **API keys** live in `.env` (git-ignored); each member uses their own key.
5. **Advice disclaimer:** the reasoning agent offers general budgeting suggestions, not financial advice. Keep that wording in any UI.
