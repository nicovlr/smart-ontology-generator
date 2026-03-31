"""
Smart Ontology Generator — CLI Principal
Orchestre le flow complet : parse → analyse → validation → création Foundry.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from ontology_generator.parser import parse_csv
from ontology_generator.analyzer import analyze_schema
from ontology_generator.formatter import format_ontology, format_ontology_summary
from ontology_generator.foundry_creator import (
    generate_entity_csvs,
    build_creation_plan,
    format_plan,
)


def main():
    args = parse_args()

    # --- Module 1 : Parse ---
    print(f"\n[1/4] Parsing de {args.csv}...")
    schema = parse_csv(args.csv)
    print(f"  -> {schema['row_count']} lignes, {len(schema['columns'])} colonnes")
    print(f"  -> Colonnes : {', '.join(c['name'] for c in schema['columns'])}")

    if args.schema_only:
        print(json.dumps(schema, indent=2, ensure_ascii=False))
        return

    # --- Module 2 : Analyse sémantique ---
    print(f"\n[2/4] Analyse sémantique via Claude ({args.model})...")
    ontology = analyze_schema(schema, model=args.model)
    print(f"  -> {format_ontology_summary(ontology)}")

    # --- Module 3 : Affichage + Validation ---
    print(f"\n[3/4] Ontologie proposée :\n")
    print(format_ontology(ontology))

    if not args.auto_approve:
        ontology = validation_loop(ontology, schema, args.model)

    # Sauvegarder l'ontologie validée
    ontology_path = os.path.join(args.output_dir, "ontology.json")
    os.makedirs(args.output_dir, exist_ok=True)
    with open(ontology_path, "w", encoding="utf-8") as f:
        json.dump(ontology, f, indent=2, ensure_ascii=False)
    print(f"\n  Ontologie sauvegardée : {ontology_path}")

    # --- Module 4 : Préparation Foundry ---
    if args.prepare_foundry:
        print(f"\n[4/4] Préparation des ressources Foundry...")

        # Générer les CSV par entité
        csv_dir = os.path.join(args.output_dir, "datasets")
        csv_paths = generate_entity_csvs(args.csv, ontology, csv_dir)
        print(f"  -> {len(csv_paths)} CSV générés dans {csv_dir}/")
        for ot_id, path in csv_paths.items():
            print(f"     - {ot_id}: {path}")

        # Construire le plan d'exécution
        plan = build_creation_plan(
            ontology=ontology,
            csv_paths=csv_paths,
            ontology_rid=args.ontology_rid or "__ONTOLOGY_RID__",
            branch_rid=args.branch_rid or "__BRANCH_RID__",
            foundry_folder=args.foundry_folder or "__FOUNDRY_FOLDER__",
        )

        plan_path = os.path.join(args.output_dir, "creation_plan.json")
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)

        print(f"\n{format_plan(plan)}")
        print(f"\n  Plan sauvegardé : {plan_path}")
        print(
            "\n  Pour exécuter ce plan dans Claude Code, lancez :\n"
            "    claude --continue\n"
            "    puis demandez : 'Exécute le plan creation_plan.json sur Foundry'\n"
        )
    else:
        print(
            "\n[4/4] Skipped (ajoutez --prepare-foundry pour générer le plan Foundry)"
        )

    print("\nTerminé !")


def validation_loop(ontology: dict, schema: dict, model: str) -> dict:
    """Boucle interactive de validation/modification de l'ontologie."""
    while True:
        print("\nOptions :")
        print("  [v] Valider tel quel")
        print("  [r] Réanalyser avec des instructions supplémentaires")
        print("  [j] Modifier le JSON directement")
        print("  [q] Quitter sans créer")

        choice = input("\nChoix : ").strip().lower()

        if choice == "v":
            print("  Ontologie validée !")
            return ontology

        elif choice == "r":
            instructions = input("Instructions supplémentaires : ").strip()
            if instructions:
                print(f"\n  Réanalyse en cours avec : '{instructions}'...")
                # On ajoute les instructions au schema pour que Claude les prenne en compte
                schema_with_instructions = {
                    **schema,
                    "user_instructions": instructions,
                }
                ontology = analyze_schema(schema_with_instructions, model=model)
                print(f"\n  -> {format_ontology_summary(ontology)}")
                print(format_ontology(ontology))

        elif choice == "j":
            print("  Entrez le JSON modifié (terminez par une ligne vide) :")
            lines = []
            while True:
                line = input()
                if line.strip() == "":
                    break
                lines.append(line)
            try:
                ontology = json.loads("\n".join(lines))
                print(f"  -> JSON mis à jour : {format_ontology_summary(ontology)}")
                print(format_ontology(ontology))
            except json.JSONDecodeError as e:
                print(f"  Erreur JSON : {e}")

        elif choice == "q":
            print("  Abandon.")
            sys.exit(0)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Smart Ontology Generator — Génère des ontologies Palantir Foundry à partir de fichiers CSV"
    )
    parser.add_argument("csv", help="Chemin vers le fichier CSV source")
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="Modèle Claude à utiliser (default: claude-sonnet-4-20250514)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Dossier de sortie (default: output/)",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Valider automatiquement sans confirmation",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Afficher uniquement le schema parsé (pas d'analyse)",
    )
    parser.add_argument(
        "--prepare-foundry",
        action="store_true",
        help="Générer les CSV par entité et le plan d'exécution MCP",
    )
    parser.add_argument(
        "--ontology-rid",
        help="Ontology RID Foundry (ri.ontology.main.ontology.{UUID})",
    )
    parser.add_argument(
        "--branch-rid",
        help="Branch RID Foundry (ri.branch..branch.{UUID})",
    )
    parser.add_argument(
        "--foundry-folder",
        help="Chemin du folder Foundry pour les datasets",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
