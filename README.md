# Stripe DES Export

Export Stripe data for the DES (Déclaration Européenne de Services) - EU intra-community clients invoices.

## Setup

```bash
uv sync
```

## Configuration

Create a `.env` file at the project root:

```env
STRIPE_API_KEY=sk_live_your_api_key_here
```

Or pass it via command line: `--api-key sk_live_xxx`

## Usage

```bash
# Export current year (default)
uv run python main.py

# Export specific year
uv run python main.py --year 2024

# Custom output file
uv run python main.py --year 2024 -o custom_export.csv
```

The script automatically scans all 12 months of the specified year and generates `des_export_YYYY.csv`.

# stripe-des
