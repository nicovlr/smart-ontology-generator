"""
Module 4 : Créateur Foundry via MCP
Transforme l'ontologie validée en plan d'exécution MCP + génère les CSV par entité.
"""

import csv
import json
import os
import re
from pathlib import Path
from typing import Any


FOUNDRY_TYPE_MAP = {
    "STRING": {"type": "string"},
    "INTEGER": {"type": "integer"},
    "LONG": {"type": "long"},
    "DOUBLE": {"type": "double"},
    "BOOLEAN": {"type": "boolean"},
    "TIMESTAMP": {"type": "timestamp"},
    "DATE": {"type": "date"},
}


def generate_entity_csvs(
    source_csv: str, ontology: dict, output_dir: str
) -> dict[str, str]:
    """
    Génère un CSV par Object Type détecté en extrayant les données
    pertinentes du CSV source.

    Returns:
        Dict mapping object_type_id -> chemin du CSV généré
    """
    os.makedirs(output_dir, exist_ok=True)

    # Lire le CSV source
    with open(source_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        source_rows = list(reader)
        source_headers = reader.fieldnames or []

    csv_paths: dict[str, str] = {}

    for ot in ontology["object_types"]:
        ot_id = ot["id"]
        properties = ot["properties"]
        source_cols = ot.get("source_columns", [])
        prop_ids = [p["id"] for p in properties]

        # Déterminer si c'est une entité "extraite" (source = 1 seule colonne != props)
        is_extracted = (
            len(source_cols) == 1
            and source_cols[0] not in prop_ids
        )

        rows: list[dict] = []
        seen_pks: set[str] = set()

        for source_row in source_rows:
            row: dict[str, Any] = {}

            if is_extracted:
                # Entité extraite d'une seule colonne (ex: Bureau from "bureau", Projet from "projet_en_cours")
                source_val = source_row.get(source_cols[0], "").strip()
                if not source_val:
                    continue
                for prop in properties:
                    row[prop["id"]] = _transform_value(source_val, prop, source_cols[0])
            else:
                # Entité principale : mapping direct colonne -> propriété
                for prop in properties:
                    prop_id = prop["id"]
                    mapped = False

                    # 1) Match exact par nom dans source_cols
                    if prop_id in source_cols and prop_id in source_headers:
                        row[prop_id] = source_row.get(prop_id, "").strip()
                        mapped = True

                    # 2) Match exact dans toutes les colonnes
                    if not mapped and prop_id in source_headers:
                        row[prop_id] = source_row.get(prop_id, "").strip()
                        mapped = True

                    if not mapped:
                        row[prop_id] = ""

            # Dédupliquer par PK
            pk_val = str(row.get(ot["primary_key"], ""))
            if pk_val and pk_val not in seen_pks:
                seen_pks.add(pk_val)
                rows.append(row)

        # Écrire le CSV
        csv_path = os.path.join(output_dir, f"{ot_id}.csv")
        if rows:
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=prop_ids)
                writer.writeheader()
                writer.writerows(rows)
        else:
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(prop_ids)

        csv_paths[ot_id] = csv_path

    return csv_paths


def _transform_value(val: str, prop: dict, source_col: str) -> str:
    """Transforme une valeur source en valeur pour l'entité cible."""
    if not val or not val.strip():
        return ""

    prop_id = prop["id"]

    # Extraction de ville depuis un pattern "Ville-Code"
    if prop_id == "ville" and "-" in val:
        return val.split("-")[0]

    # Extraction de code depuis un pattern "Ville-Code"
    if prop_id in ("code", "code_bureau") and "-" in val:
        return val  # Garder le code complet comme PK

    return val.strip()


def build_creation_plan(
    ontology: dict,
    csv_paths: dict[str, str],
    ontology_rid: str,
    branch_rid: str,
    foundry_folder: str,
) -> dict:
    """
    Construit le plan d'exécution : liste ordonnée d'opérations MCP.

    Returns:
        {
            "steps": [
                {"operation": "create_dataset", "params": {...}},
                {"operation": "create_object_type", "params": {...}},
                {"operation": "create_link_type", "params": {...}},
            ]
        }
    """
    steps: list[dict] = []

    # Phase 1 : Créer les datasets
    for ot in ontology["object_types"]:
        ot_id = ot["id"]
        csv_path = csv_paths.get(ot_id)
        if not csv_path:
            continue

        # Schema du dataset
        dataset_schema = []
        for prop in ot["properties"]:
            foundry_type = FOUNDRY_TYPE_MAP.get(prop["type"], {"type": "string"})
            col = {
                "name": prop["id"],
                "nullable": prop.get("nullable", False),
                **foundry_type,
            }
            if foundry_type.get("type") == "timestamp":
                col["dateFormat"] = "yyyy-MM-dd'T'HH:mm:ss"
            dataset_schema.append(col)

        steps.append({
            "operation": "create_dataset",
            "entity_id": ot_id,
            "params": {
                "name": f"dataset_{ot_id}",
                "csvFilePath": csv_path,
                "foundryLocation": {"folderPath": foundry_folder},
                "schema": dataset_schema,
                "primaryKey": {"columns": [ot["primary_key"]]},
            },
        })

    # Phase 2 : Créer les object types (après les datasets, car on a besoin des RIDs)
    for ot in ontology["object_types"]:
        property_types = []
        for prop in ot["properties"]:
            foundry_type = FOUNDRY_TYPE_MAP.get(prop["type"], {"type": "string"})
            api_name = _to_camel_case(prop["id"])
            pt = {
                "propertyTypeId": prop["id"],
                "displayMetadata": {
                    "displayName": prop.get("display_name", prop["id"]),
                },
                "type": foundry_type,
                "isNullable": prop.get("nullable", False),
            }
            if prop.get("description"):
                pt["displayMetadata"]["description"] = prop["description"]
            if api_name:
                pt["apiName"] = api_name
            property_types.append(pt)

        # Property mapping (colonne -> propriété)
        property_mapping = []
        for prop in ot["properties"]:
            property_mapping.append({
                "propertyTypeId": prop["id"],
                "mappingInfo": {"type": "column", "column": prop["id"]},
            })

        steps.append({
            "operation": "create_object_type",
            "entity_id": ot["id"],
            "depends_on_dataset": ot["id"],
            "params": {
                "ontologyRid": ontology_rid,
                "foundryBranchRid": branch_rid,
                "modificationType": "CREATE",
                "displayName": ot["display_name"],
                "pluralDisplayName": ot.get("plural_display_name", ot["display_name"] + "s"),
                "apiName": ot.get("api_name", _to_pascal_case(ot["id"])),
                "objectTypeId": ot["id"],
                "primaryKey": ot["primary_key"],
                "titlePropertyTypeId": ot.get("title_property", ot["primary_key"]),
                "propertyTypes": property_types,
                "backingDataset": {
                    "datasetRid": f"__PLACEHOLDER_DATASET_RID_{ot['id']}__",
                    "propertyMapping": property_mapping,
                },
            },
        })

    # Phase 3 : Créer les link types (après les object types)
    for lt in ontology["link_types"]:
        steps.append({
            "operation": "create_link_type",
            "entity_id": lt["id"],
            "params": {
                "ontologyRid": ontology_rid,
                "foundryBranchRid": branch_rid,
                "modificationType": "CREATE",
                "displayName": lt.get("display_name", lt["id"]),
                "pluralDisplayName": lt.get("plural_display_name", lt.get("display_name", lt["id"]) + "s"),
                "apiName": lt.get("api_name", _to_camel_case(lt["id"])),
                "linkTypeId": lt["id"],
                "leftSide": {
                    "objectTypeId": lt["from_object"],
                    "propertyId": lt.get("from_property", ""),
                },
                "rightSide": {
                    "objectTypeId": lt["to_object"],
                    "propertyId": lt.get("to_property", ""),
                },
                "leftToRightLinkMetadata": {
                    "displayName": lt.get("left_to_right_label", lt.get("display_name", "")),
                    "pluralDisplayName": lt.get("left_to_right_label", lt.get("display_name", "")) + "s",
                },
                "rightToLeftLinkMetadata": {
                    "displayName": lt.get("right_to_left_label", ""),
                    "pluralDisplayName": lt.get("right_to_left_label", "") + "s",
                },
            },
        })

    return {"steps": steps}


def _to_camel_case(s: str) -> str:
    parts = re.split(r"[-_]", s)
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def _to_pascal_case(s: str) -> str:
    parts = re.split(r"[-_]", s)
    return "".join(p.capitalize() for p in parts)


def format_plan(plan: dict) -> str:
    """Affiche le plan d'exécution de manière lisible."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("  PLAN D'EXÉCUTION FOUNDRY")
    lines.append("=" * 60)

    for i, step in enumerate(plan["steps"], 1):
        op = step["operation"]
        entity = step["entity_id"]
        icon = {"create_dataset": "DB", "create_object_type": "OT", "create_link_type": "LT"}.get(op, "??")
        lines.append(f"\n  [{icon}] Étape {i}: {op}")
        lines.append(f"        Entité: {entity}")

        if op == "create_dataset":
            lines.append(f"        Fichier: {step['params']['csvFilePath']}")
            lines.append(f"        PK: {step['params'].get('primaryKey', {}).get('columns', [])}")
        elif op == "create_object_type":
            p = step["params"]
            n_props = len(p.get("propertyTypes", []))
            lines.append(f"        Display: {p['displayName']} | API: {p['apiName']}")
            lines.append(f"        {n_props} propriété(s) | PK: {p['primaryKey']}")
        elif op == "create_link_type":
            p = step["params"]
            left = p["leftSide"]["objectTypeId"]
            right = p["rightSide"]["objectTypeId"]
            lines.append(f"        {left} --> {right}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


if __name__ == "__main__":
    print("Module foundry_creator chargé. Utilisez build_creation_plan() pour générer un plan.")
