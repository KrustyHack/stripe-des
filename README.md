# Stripe DES Export

Export Stripe invoices data for the **Déclaration Européenne de Services** (DES) - a mandatory French tax declaration for B2B services provided to intra-EU clients.

## Overview

This tool extracts paid invoices from your Stripe account and generates a CSV report containing:
- Intra-EU clients (excluding France)
- VAT numbers (EU VAT IDs)
- Total amounts billed (excluding tax)
- Invoice counts per client

The output is formatted for easy import into French DES tax filing systems.

## Requirements

- Python 3.11+
- Stripe API key with read access to invoices and customers
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

## Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/krustyhack/stripe-des.git
cd stripe-des

# Install dependencies
uv sync
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
STRIPE_API_KEY=sk_live_your_api_key_here
```

| Variable | Description | Required |
|----------|-------------|----------|
| `STRIPE_API_KEY` | Your Stripe live or test API key | Yes |

### Supported EU Countries

The tool exports data for clients from these EU member states (France is excluded as it's the declaring country):

| Code | Country |
|------|---------|
| AT | Austria |
| BE | Belgium |
| BG | Bulgaria |
| CY | Cyprus |
| CZ | Czech Republic |
| DE | Germany |
| DK | Denmark |
| EE | Estonia |
| ES | Spain |
| FI | Finland |
| GR | Greece |
| HR | Croatia |
| HU | Hungary |
| IE | Ireland |
| IT | Italy |
| LT | Lithuania |
| LU | Luxembourg |
| LV | Latvia |
| MT | Malta |
| NL | Netherlands |
| PL | Poland |
| PT | Portugal |
| RO | Romania |
| SE | Sweden |
| SI | Slovenia |
| SK | Slovakia |

## Usage

### Basic Usage

Export the current year's data:

```bash
uv run python main.py
```

### Command Line Options

```bash
python main.py [OPTIONS]

Options:
  -y, --year YEAR      Year to export (default: current year)
  -o, --output FILE    Output CSV filename (default: output/des_export_YYYY.csv)
  --api-key KEY        Stripe API key (overrides STRIPE_API_KEY env var)
```

### Examples

Export 2024 data:
```bash
uv run python main.py --year 2024
```

Export to a specific file:
```bash
uv run python main.py --year 2024 --output my_des_report.csv
```

Use a specific API key:
```bash
uv run python main.py --api-key sk_live_xxxxx
```

## Output

### CSV Format

The generated CSV file uses semicolon (`;`) as delimiter and contains:

| Column | Description |
|--------|-------------|
| Code Pays | ISO 3166-1 alpha-2 country code |
| Pays | Country name (in French) |
| Numéro TVA | EU VAT number (if available) |
| Nom Client | Customer name |
| Email | Customer email |
| Montant HT (EUR) | Total amount excluding tax (in EUR) |
| Nb Factures | Number of invoices |

### Console Output

The script displays:
1. Progress during invoice fetching
2. Monthly breakdown of clients and amounts
3. Summary by country
4. Complete client list with totals

Example output:
```
Récupération des factures pour l'année 2024...
  → 01/2024: 15 factures
  → 02/2024: 22 factures
  ...
  → Total: 180 factures payées
  → 12 clients intra-UE (hors France)
  → Export CSV: output/des_export_2024.csv

══════════════════════════════════════════════════════════
  EXPORT DES - 01/2024 → 12/2024
══════════════════════════════════════════════════════════
...
```

## How It Works

### Data Flow

```
Stripe API → Fetch Invoices → Filter EU Clients → Aggregate → CSV Export
                                    ↓
                            Extract VAT Numbers
```

### Invoice Processing

1. **Fetch**: Retrieves all paid invoices for the specified year
2. **Filter**: Keeps only clients with addresses in EU countries (excluding France)
3. **Aggregate**: Groups by customer, summing subtotals (amounts before tax)
4. **Export**: Generates CSV sorted by country code

### Customer Country Detection

The tool extracts customer country from (in priority order):
1. Customer billing address
2. Shipping address (fallback)

### VAT Number Extraction

EU VAT numbers are extracted from Stripe's tax IDs associated with each customer.

## Project Structure

```
stripe-des/
├── main.py              # Main script with all functionality
├── pyproject.toml       # Project configuration and dependencies
├── .env                 # Environment variables (not in git)
├── .gitignore           # Git ignore rules
├── .python-version      # Python version (3.11)
└── output/              # Generated reports directory
    └── des_export_*.csv # CSV exports
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/krustyhack/stripe-des.git
cd stripe-des

# Create virtual environment with uv
uv venv
source .venv/bin/activate

# Install dependencies
uv sync
```

### Running with Test Mode

Use Stripe's test API key to validate the script without affecting live data:

```bash
STRIPE_API_KEY=sk_test_xxxxx uv run python main.py --year 2024
```

## Legal Context

The **Déclaration Européenne de Services (DES)** is a French tax obligation requiring businesses to declare B2B services provided to clients in other EU member states. This declaration is submitted monthly to French customs and is used for:

- Intra-community trade statistics
- VAT fraud prevention
- Cross-border service monitoring

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request
