#!/usr/bin/env python3
"""Compute stats over a full cijene-api crawl and extract a per-city sample.

Input:  <crawl_dir>/<chain>/{stores,products,prices}.csv  (cijene-api crawler output)
Output: <out_dir>/<chain>/{stores,products,prices}.csv.gz  (prices/stores only for <city>)
        <out_dir>/<chain>/stats.json                        (computed over ALL stores)

Standard library only, so it runs next to the crawler without extra installs.
"""

import argparse
import csv
import gzip
import json
import re
import statistics
from pathlib import Path

EAN_RE = re.compile(r"^\d{8,14}$")


def to_float(value: str) -> float | None:
    value = (value or "").strip().replace(",", ".")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def write_gz(path: Path, rows: list[dict], columns: list[str]) -> None:
    with gzip.open(path, "wt", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def process_chain(chain_dir: Path, out_dir: Path, city: str) -> dict:
    chain = chain_dir.name
    stores_path = chain_dir / "stores.csv"
    products_path = chain_dir / "products.csv"
    prices_path = chain_dir / "prices.csv"

    with open(stores_path, newline="", encoding="utf-8") as f:
        stores = list(csv.DictReader(f))
    with open(products_path, newline="", encoding="utf-8") as f:
        products = list(csv.DictReader(f))

    city_key = city.strip().lower()
    city_store_ids = {s["store_id"] for s in stores if s["city"].strip().lower() == city_key}

    ean_count = sum(1 for p in products if EAN_RE.match((p.get("barcode") or "").strip()))

    # Per product: min/max regular price and distinct price set across stores.
    per_product: dict[str, dict] = {}
    n_prices = 0
    n_special = 0
    n_special_below_best30 = 0
    n_special_with_best30 = 0
    city_prices: list[dict] = []
    price_columns: list[str] = []

    with open(prices_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        price_columns = list(reader.fieldnames or [])
        for row in reader:
            n_prices += 1
            price = to_float(row.get("price", ""))
            special = to_float(row.get("special_price", ""))
            best30 = to_float(row.get("best_price_30", ""))
            if special is not None:
                n_special += 1
                if best30 is not None:
                    n_special_with_best30 += 1
                    if special < best30:
                        n_special_below_best30 += 1
            if price is not None:
                entry = per_product.setdefault(row["product_id"], {"min": price, "max": price, "values": set()})
                entry["min"] = min(entry["min"], price)
                entry["max"] = max(entry["max"], price)
                if len(entry["values"]) < 50:
                    entry["values"].add(price)
            if row["store_id"] in city_store_ids:
                city_prices.append(row)

    varying = [e for e in per_product.values() if len(e["values"]) > 1]
    rel_ranges = [(e["max"] - e["min"]) / e["min"] for e in varying if e["min"] > 0]

    chain_out = out_dir / chain
    chain_out.mkdir(parents=True, exist_ok=True)
    write_gz(chain_out / "stores.csv.gz", [s for s in stores if s["store_id"] in city_store_ids], list(stores[0].keys()) if stores else [])
    write_gz(chain_out / "products.csv.gz", products, list(products[0].keys()) if products else [])
    write_gz(chain_out / "prices.csv.gz", city_prices, price_columns)

    stats = {
        "chain": chain,
        "stores_total": len(stores),
        "stores_in_city": len(city_store_ids),
        "city": city,
        "products": len(products),
        "products_with_ean": ean_count,
        "prices_total": n_prices,
        "prices_in_city": len(city_prices),
        "special_price_rows": n_special,
        "special_rows_with_best30": n_special_with_best30,
        "special_below_best30": n_special_below_best30,
        "products_priced": len(per_product),
        "products_with_varying_price_across_stores": len(varying),
        "varying_price_rel_range_median": statistics.median(rel_ranges) if rel_ranges else 0,
        "varying_price_rel_range_p90": statistics.quantiles(rel_ranges, n=10)[-1] if len(rel_ranges) >= 10 else None,
        "raw_bytes": {
            "stores": stores_path.stat().st_size,
            "products": products_path.stat().st_size,
            "prices": prices_path.stat().st_size,
        },
    }
    (chain_out / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("crawl_dir", type=Path, help="Directory with <chain>/ subfolders")
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--city", default="Split")
    args = parser.parse_args()

    chain_dirs = sorted(p for p in args.crawl_dir.iterdir() if (p / "prices.csv").exists())
    if not chain_dirs:
        print(f"No chain data found in {args.crawl_dir}")
        return 1
    for chain_dir in chain_dirs:
        stats = process_chain(chain_dir, args.out_dir, args.city)
        print(json.dumps(stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
