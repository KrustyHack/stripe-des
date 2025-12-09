#!/usr/bin/env python3
"""
Script d'export Stripe pour la DES (Déclaration Européenne de Services)
Extrait les clients intra-UE (hors France) avec leurs montants facturés.
"""

import stripe
import csv
import os
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "sk_live_xxx")

# Pays UE (hors France) - ISO 3166-1 alpha-2
EU_COUNTRIES = {
    "AT": "Autriche",
    "BE": "Belgique",
    "BG": "Bulgarie",
    "HR": "Croatie",
    "CY": "Chypre",
    "CZ": "Tchéquie",
    "DK": "Danemark",
    "EE": "Estonie",
    "FI": "Finlande",
    "DE": "Allemagne",
    "GR": "Grèce",
    "HU": "Hongrie",
    "IE": "Irlande",
    "IT": "Italie",
    "LV": "Lettonie",
    "LT": "Lituanie",
    "LU": "Luxembourg",
    "MT": "Malte",
    "NL": "Pays-Bas",
    "PL": "Pologne",
    "PT": "Portugal",
    "RO": "Roumanie",
    "SK": "Slovaquie",
    "SI": "Slovénie",
    "ES": "Espagne",
    "SE": "Suède",
}


@dataclass
class ClientDES:
    """Données client pour la DES"""
    customer_id: str
    name: str
    email: str
    country_code: str
    country_name: str
    vat_number: Optional[str]
    total_ht_cents: int
    invoice_count: int
    
    @property
    def total_ht_euros(self) -> float:
        return self.total_ht_cents / 100


def get_month_range(year: int, month: int) -> tuple[int, int]:
    """Retourne les timestamps Unix pour le début et la fin du mois."""
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return int(start.timestamp()), int(end.timestamp())


def get_current_year() -> int:
    """Retourne l'année courante."""
    return datetime.now().year


def get_year_months(year: int) -> list[tuple[int, int]]:
    """Retourne la liste des 12 mois pour une année donnée."""
    return [(year, month) for month in range(1, 13)]


def fetch_invoices(start_ts: int, end_ts: int) -> list:
    """Récupère toutes les factures payées sur la période."""
    invoices = []
    has_more = True
    starting_after = None
    
    while has_more:
        params = {
            "created": {"gte": start_ts, "lt": end_ts},
            "status": "paid",
            "limit": 100,
            "expand": ["data.customer"],
        }
        if starting_after:
            params["starting_after"] = starting_after
            
        response = stripe.Invoice.list(**params)
        invoices.extend(response.data)
        has_more = response.has_more
        if invoices:
            starting_after = invoices[-1].id
            
    return invoices


def extract_customer_country(customer) -> Optional[str]:
    """Extrait le code pays du client depuis différentes sources."""
    # Priorité : tax_ids > address > shipping
    if customer.address and customer.address.country:
        return customer.address.country
    if hasattr(customer, 'shipping') and customer.shipping and customer.shipping.address:
        return customer.shipping.address.country
    return None


def extract_vat_number(customer) -> Optional[str]:
    """Extrait le numéro de TVA intra-communautaire du client."""
    try:
        tax_ids = stripe.Customer.list_tax_ids(customer.id, limit=10)
        for tax_id in tax_ids.data:
            if tax_id.type == "eu_vat":
                return tax_id.value
    except Exception:
        pass
    return None


def aggregate_by_client(invoices: list) -> dict[str, ClientDES]:
    """Agrège les factures par client UE (hors France)."""
    clients = {}
    
    for invoice in invoices:
        customer = invoice.customer
        if not customer:
            continue
            
        country_code = extract_customer_country(customer)
        if not country_code or country_code not in EU_COUNTRIES:
            continue
            
        customer_id = customer.id
        
        if customer_id not in clients:
            clients[customer_id] = ClientDES(
                customer_id=customer_id,
                name=customer.name or "",
                email=customer.email or "",
                country_code=country_code,
                country_name=EU_COUNTRIES[country_code],
                vat_number=extract_vat_number(customer),
                total_ht_cents=0,
                invoice_count=0,
            )
        
        # Montant HT (subtotal = montant avant taxes)
        clients[customer_id].total_ht_cents += invoice.subtotal or 0
        clients[customer_id].invoice_count += 1
        
    return clients


def export_csv(clients: dict[str, ClientDES], filename: str):
    """Exporte les données au format CSV."""
    # Ensure output directory exists
    output_dir = os.path.dirname(filename)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "Code Pays",
            "Pays",
            "Numéro TVA",
            "Nom Client",
            "Email",
            "Montant HT (EUR)",
            "Nb Factures",
        ])
        
        for client in sorted(clients.values(), key=lambda c: c.country_code):
            writer.writerow([
                client.country_code,
                client.country_name,
                client.vat_number or "",
                client.name,
                client.email,
                f"{client.total_ht_euros:.2f}",
                client.invoice_count,
            ])


def print_month_summary(clients: dict[str, ClientDES], year: int, month: int):
    """Affiche un résumé pour un mois donné."""
    print(f"\n{'─'*70}")
    print(f"  {month:02d}/{year}")
    print(f"{'─'*70}")
    
    if not clients:
        print("  Aucun client intra-UE trouvé.\n")
        return 0.0
    
    # Liste des clients du mois
    print(f"  {'Pays':<6} {'Client':<28} {'TVA':<18} {'Montant HT':>12}")
    print(f"  {'-'*66}")
    
    month_total = 0.0
    for client in sorted(clients.values(), key=lambda c: (c.country_code, c.name)):
        name = client.name[:26] + ".." if len(client.name) > 28 else client.name
        vat = client.vat_number or "-"
        vat = vat[:16] + ".." if len(vat) > 18 else vat
        print(f"  {client.country_code:<6} {name:<28} {vat:<18} {client.total_ht_euros:>11,.2f}€")
        month_total += client.total_ht_euros
    
    print(f"  {'-'*66}")
    print(f"  {'TOTAL':<6} {len(clients)} client(s){' '*26} {month_total:>11,.2f}€")
    
    return month_total


def print_summary(invoices_by_month: dict[tuple[int, int], list], periods: list[tuple[int, int]], all_clients: dict[str, ClientDES]):
    """Affiche un résumé détaillé par mois + récapitulatif global."""
    print(f"\n{'='*60}")
    if len(periods) == 1:
        year, month = periods[0]
        print(f"  EXPORT DES - {month:02d}/{year}")
    else:
        start_year, start_month = periods[0]
        end_year, end_month = periods[-1]
        print(f"  EXPORT DES - {start_month:02d}/{start_year} → {end_month:02d}/{end_year}")
    print(f"{'='*60}")
    
    # Détail par mois
    grand_total = 0.0
    for year, month in periods:
        invoices = invoices_by_month.get((year, month), [])
        clients = aggregate_by_client(invoices)
        month_total = print_month_summary(clients, year, month)
        grand_total += month_total
    
    # Récapitulatif global
    print(f"\n{'='*60}")
    print("  RÉCAPITULATIF GLOBAL")
    print(f"{'='*60}")
    
    if not all_clients:
        print("\n  Aucun client intra-UE trouvé sur la période.\n")
        return
    
    # Totaux par pays
    print("\n  📊 TOTAUX PAR PAYS")
    print(f"  {'-'*50}")
    by_country = defaultdict(lambda: {"clients": [], "total": 0})
    for client in all_clients.values():
        by_country[client.country_code]["clients"].append(client)
        by_country[client.country_code]["total"] += client.total_ht_euros
    
    print(f"  {'Pays':<20} {'Clients':>8} {'Montant HT':>18}")
    print(f"  {'-'*50}")
    for code in sorted(by_country.keys()):
        data = by_country[code]
        country_name = EU_COUNTRIES[code]
        print(f"  {country_name:<20} {len(data['clients']):>8} {data['total']:>17,.2f}€")
    
    print(f"  {'-'*50}")
    print(f"  {'TOTAL':<20} {len(all_clients):>8} {grand_total:>17,.2f}€")
    
    # Liste des clients
    print(f"\n  👥 LISTE DES CLIENTS ({len(all_clients)})")
    print(f"  {'-'*70}")
    print(f"  {'Pays':<12} {'Client':<25} {'TVA':<18} {'Montant HT':>12}")
    print(f"  {'-'*70}")
    
    for client in sorted(all_clients.values(), key=lambda c: (c.country_code, c.name)):
        name = client.name[:23] + ".." if len(client.name) > 25 else client.name
        vat = client.vat_number or "-"
        vat = vat[:16] + ".." if len(vat) > 18 else vat
        print(f"  {client.country_code:<12} {name:<25} {vat:<18} {client.total_ht_euros:>11,.2f}€")
    
    print(f"  {'-'*70}")
    print(f"\n{'='*60}")
    print(f"  TOTAL GÉNÉRAL: {grand_total:,.2f}€")
    print(f"{'='*60}\n")


def main():
    """Point d'entrée principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Export Stripe pour la DES (Déclaration Européenne de Services)")
    parser.add_argument("--year", "-y", type=int, help="Année à exporter (défaut: année courante)")
    parser.add_argument("--output", "-o", help="Fichier de sortie (défaut: output/des_export_YYYY.csv)")
    parser.add_argument("--api-key", help="Clé API Stripe (ou env STRIPE_API_KEY)")
    args = parser.parse_args()
    
    # Configuration Stripe
    stripe.api_key = args.api_key or STRIPE_API_KEY
    if stripe.api_key == "sk_live_xxx":
        print("ERREUR: Configurez votre clé API Stripe via --api-key ou STRIPE_API_KEY")
        return 1
    
    # Année à traiter
    year = args.year or get_current_year()
    
    # Fichier de sortie (par défaut dans output/)
    output_file = args.output or f"output/des_export_{year}.csv"
    
    # Liste des 12 mois de l'année
    periods = get_year_months(year)
    
    print(f"Récupération des factures pour l'année {year}...")
    
    # Extraction pour tous les mois
    invoices_by_month: dict[tuple[int, int], list] = {}
    all_invoices = []
    
    for year, month in periods:
        start_ts, end_ts = get_month_range(year, month)
        invoices = fetch_invoices(start_ts, end_ts)
        invoices_by_month[(year, month)] = invoices
        all_invoices.extend(invoices)
        print(f"  → {month:02d}/{year}: {len(invoices)} factures")
    
    print(f"  → Total: {len(all_invoices)} factures payées")
    
    # Agrégation globale pour l'export CSV
    clients = aggregate_by_client(all_invoices)
    print(f"  → {len(clients)} clients intra-UE (hors France)")
    
    # Export
    export_csv(clients, output_file)
    print(f"  → Export CSV: {output_file}")
    
    # Résumé détaillé par mois + récapitulatif global
    print_summary(invoices_by_month, periods, clients)
    
    return 0


if __name__ == "__main__":
    exit(main())
