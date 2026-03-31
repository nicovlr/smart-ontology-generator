"""Test du flow complet avec une ontologie simulée (sans appel API)."""

import json
from ontology_generator.parser import parse_csv
from ontology_generator.formatter import format_ontology, format_ontology_summary
from ontology_generator.foundry_creator import generate_entity_csvs, build_creation_plan, format_plan

# Module 1 : Parse
print("[1/4] Parsing...")
schema = parse_csv("sample_data/employes.csv")
print(f"  -> {schema['row_count']} lignes, {len(schema['columns'])} colonnes\n")

# Module 2 : Simuler la réponse Claude
print("[2/4] Analyse sémantique (simulée)...")
ontology = {
    "object_types": [
        {
            "id": "employe",
            "display_name": "Employé",
            "plural_display_name": "Employés",
            "api_name": "Employe",
            "description": "Représente un employé de l'entreprise",
            "primary_key": "nom",
            "title_property": "nom",
            "properties": [
                {"id": "nom", "display_name": "Nom", "type": "STRING", "nullable": False, "description": "Nom de l'employé (identifiant unique)"},
                {"id": "chef", "display_name": "Chef", "type": "STRING", "nullable": True, "description": "Nom du manager (FK vers Employé)"},
                {"id": "bureau", "display_name": "Bureau", "type": "STRING", "nullable": False, "description": "Code bureau (FK vers Bureau)"},
                {"id": "projet_en_cours", "display_name": "Projet en cours", "type": "STRING", "nullable": False, "description": "Nom du projet (FK vers Projet)"},
            ],
            "source_columns": ["nom", "chef", "bureau", "projet_en_cours"],
        },
        {
            "id": "bureau",
            "display_name": "Bureau",
            "plural_display_name": "Bureaux",
            "api_name": "Bureau",
            "description": "Lieu de travail physique avec ville et code",
            "primary_key": "code",
            "title_property": "code",
            "properties": [
                {"id": "code", "display_name": "Code Bureau", "type": "STRING", "nullable": False, "description": "Identifiant unique du bureau (ex: Paris-3A)"},
                {"id": "ville", "display_name": "Ville", "type": "STRING", "nullable": False, "description": "Ville du bureau"},
            ],
            "source_columns": ["bureau"],
        },
        {
            "id": "projet",
            "display_name": "Projet",
            "plural_display_name": "Projets",
            "api_name": "Projet",
            "description": "Projet en cours dans l'entreprise",
            "primary_key": "nom",
            "title_property": "nom",
            "properties": [
                {"id": "nom", "display_name": "Nom", "type": "STRING", "nullable": False, "description": "Nom du projet"},
            ],
            "source_columns": ["projet_en_cours"],
        },
    ],
    "link_types": [
        {
            "id": "employe-manage-par-employe",
            "display_name": "Managé par",
            "plural_display_name": "Managés par",
            "api_name": "managePar",
            "from_object": "employe",
            "from_property": "nom",
            "to_object": "employe",
            "to_property": "chef",
            "cardinality": "ONE_TO_MANY",
            "left_to_right_label": "manage",
            "right_to_left_label": "est managé par",
            "description": "Relation hiérarchique manager → subordonné",
        },
        {
            "id": "bureau-employes",
            "display_name": "Employés du bureau",
            "plural_display_name": "Employés des bureaux",
            "api_name": "bureauEmployes",
            "from_object": "bureau",
            "from_property": "code",
            "to_object": "employe",
            "to_property": "bureau",
            "cardinality": "ONE_TO_MANY",
            "left_to_right_label": "a pour employés",
            "right_to_left_label": "travaille dans",
            "description": "Affectation d'un employé à un bureau",
        },
        {
            "id": "projet-employes",
            "display_name": "Employés du projet",
            "plural_display_name": "Employés des projets",
            "api_name": "projetEmployes",
            "from_object": "projet",
            "from_property": "nom",
            "to_object": "employe",
            "to_property": "projet_en_cours",
            "cardinality": "ONE_TO_MANY",
            "left_to_right_label": "a pour employés",
            "right_to_left_label": "est assigné à",
            "description": "Assignation d'un employé à un projet",
        },
    ],
    "reasoning": "Le CSV contient 3 entités : Employé (lignes), Bureau (pattern Ville-Code, unique_ratio=0.3), Projet (valeurs partagées, unique_ratio=0.3). La colonne 'chef' référence des noms d'employés existants = relation hiérarchique self-referencing.",
}

print(f"  -> {format_ontology_summary(ontology)}\n")

# Module 3 : Affichage
print("[3/4] Ontologie proposée :\n")
print(format_ontology(ontology))

# Module 4 : Préparation Foundry
print("\n[4/4] Préparation Foundry...")
csv_paths = generate_entity_csvs("sample_data/employes.csv", ontology, "output/datasets")
print(f"  -> {len(csv_paths)} CSV générés :")
for ot_id, path in csv_paths.items():
    print(f"     - {ot_id}: {path}")

plan = build_creation_plan(
    ontology=ontology,
    csv_paths=csv_paths,
    ontology_rid="ri.ontology.main.ontology.PLACEHOLDER",
    branch_rid="ri.branch..branch.PLACEHOLDER",
    foundry_folder="/ontology-generator/datasets",
)

print(f"\n{format_plan(plan)}")

# Sauvegarder
import os
os.makedirs("output", exist_ok=True)
with open("output/ontology.json", "w") as f:
    json.dump(ontology, f, indent=2, ensure_ascii=False)
with open("output/creation_plan.json", "w") as f:
    json.dump(plan, f, indent=2, ensure_ascii=False)

print("\nFichiers générés :")
print("  - output/ontology.json")
print("  - output/creation_plan.json")
print("  - output/datasets/*.csv")
print("\nFlow complet OK !")
