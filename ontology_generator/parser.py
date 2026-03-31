"""
Module 1 : Parser CSV
Lit un fichier CSV et extrait un schema JSON normalisé avec stats.
"""

import csv
import json
import re
from pathlib import Path
from collections import Counter
from typing import Any


def detect_delimiter(file_path: str, sample_size: int = 5) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        sample = "".join(f.readline() for _ in range(sample_size))
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample)
        return dialect.delimiter
    except csv.Error:
        return ","


def infer_type(values: list[str]) -> str:
    """Infere le type de données à partir d'un échantillon de valeurs non-nulles."""
    if not values:
        return "STRING"

    # Test BOOLEAN
    bool_vals = {"true", "false", "0", "1", "yes", "no", "oui", "non"}
    if all(v.lower() in bool_vals for v in values):
        return "BOOLEAN"

    # Test INTEGER
    int_pattern = re.compile(r"^-?\d+$")
    if all(int_pattern.match(v) for v in values):
        return "INTEGER"

    # Test DOUBLE
    double_pattern = re.compile(r"^-?\d+[.,]\d+$")
    if all(double_pattern.match(v) for v in values):
        return "DOUBLE"

    # Test TIMESTAMP (formats courants)
    ts_patterns = [
        re.compile(r"^\d{4}-\d{2}-\d{2}"),  # 2024-01-15 ou 2024-01-15T10:30:00
        re.compile(r"^\d{2}/\d{2}/\d{4}"),   # 15/01/2024
    ]
    if all(any(p.match(v) for p in ts_patterns) for v in values):
        return "TIMESTAMP"

    return "STRING"


def compute_column_stats(values: list[Any]) -> dict:
    """Calcule les statistiques d'une colonne."""
    total = len(values)
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    null_count = total - len(non_null)
    unique_values = set(str(v) for v in non_null)

    return {
        "total_count": total,
        "null_count": null_count,
        "null_ratio": round(null_count / total, 2) if total > 0 else 0,
        "unique_count": len(unique_values),
        "unique_ratio": round(len(unique_values) / len(non_null), 2) if non_null else 0,
    }


def parse_csv(file_path: str, sample_size: int = 20) -> dict:
    """
    Parse un fichier CSV et retourne un schema JSON normalisé.

    Returns:
        {
            "file": "nom_du_fichier.csv",
            "row_count": 100,
            "columns": [
                {
                    "name": "col_name",
                    "type": "STRING|INTEGER|...",
                    "sample": ["val1", "val2", ...],
                    "stats": { "total_count": ..., "null_ratio": ..., ... },
                    "top_values": [("val", count), ...]
                }
            ]
        }
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")

    delimiter = detect_delimiter(file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        headers = reader.fieldnames or []

        # Lire toutes les lignes
        all_rows: list[dict] = []
        for row in reader:
            all_rows.append(row)

    row_count = len(all_rows)
    columns = []

    for header in headers:
        all_values = [row.get(header) for row in all_rows]
        non_null_values = [str(v).strip() for v in all_values if v is not None and str(v).strip() != ""]

        # Échantillon (les N premières valeurs non-nulles)
        sample_values = non_null_values[:sample_size]

        # Type inféré
        inferred_type = infer_type(non_null_values)

        # Stats
        stats = compute_column_stats(all_values)

        # Top valeurs (les 10 plus fréquentes)
        counter = Counter(non_null_values)
        top_values = counter.most_common(10)

        columns.append({
            "name": header,
            "type": inferred_type,
            "sample": sample_values,
            "stats": stats,
            "top_values": [{"value": v, "count": c} for v, c in top_values],
        })

    return {
        "file": path.name,
        "row_count": row_count,
        "delimiter": delimiter,
        "columns": columns,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python parser.py <chemin_csv>")
        sys.exit(1)

    schema = parse_csv(sys.argv[1])
    print(json.dumps(schema, indent=2, ensure_ascii=False))
