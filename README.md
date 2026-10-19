# cijene-sample

Daily sample of public Croatian retail price lists, used for prototyping.

- **Source:** price lists that retailers must publish under the Croatian
  decision on publishing price lists (NN 75/2025, extended by NN 101/2026).
- **Crawler:** [senko/cijene-api](https://github.com/senko/cijene-api)
  (AGPL-3.0), checked out unmodified at a pinned commit during the workflow
  run. Its code is not copied into this repository. The project's cleaned
  product catalogue (CC BY-NC-SA) is not used.
- **Contents of the `data` branch:** `data/<date>/<chain>/` with
  `stores.csv.gz` and `prices.csv.gz` for one city only, `products.csv.gz`
  for the whole chain, and `stats.json` computed over all stores of the chain.
- **Chains:** Konzum, Lidl, Kaufland.

Runs daily at 07:40 UTC until 2026-10-26 (one-week window). `data/latest.json` points to the newest day.

Run it manually from the Actions tab (`crawl`, optional `city` input) or by
pushing changes to the workflow or `filter_and_stats.py`.
