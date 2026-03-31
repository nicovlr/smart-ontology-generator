"""
Module 2 : Analyseur sémantique
Utilise Claude API pour analyser le schema CSV et proposer une ontologie Foundry.
"""

import json
import os
from anthropic import Anthropic

SYSTEM_PROMPT = """Tu es un expert en modélisation de données et en Palantir Foundry.
Tu analyses des schemas de fichiers de données et tu proposes des ontologies Foundry optimales.
Tu réponds UNIQUEMENT en JSON valide, sans markdown ni commentaire."""

ANALYSIS_PROMPT_TEMPLATE = """Analyse ce schema de données et propose une ontologie Palantir Foundry.

SCHEMA DU FICHIER :
{schema_json}

RÈGLES D'ANALYSE :
1. Chaque "entité" du monde réel = un Object Type Foundry
2. Si une colonne contient des valeurs qui existent dans une autre colonne (ex: "chef" contient des noms qui existent dans "nom"), c'est une RELATION (Link Type), pas une simple propriété
3. Si une colonne a un pattern récurrent (ex: "Paris-3A", "Lyon-1B"), elle peut représenter une entité composite avec plusieurs propriétés extraites (ville + code)
4. Les colonnes avec un faible ratio de valeurs uniques (unique_ratio < 0.4) sont souvent des références vers d'autres entités qu'il faut extraire en Object Types séparés
5. Les colonnes de type date/timestamp restent des propriétés, pas des entités
6. Chaque Object Type DOIT avoir une propriété qui sert de clé primaire (primary key). Si elle n'existe pas naturellement, propose d'en générer une (ex: un ID)
7. Pour les Link Types ONE_TO_MANY : le côté "many" doit contenir une foreign key qui pointe vers la primary key du côté "one"

IMPORTANT SUR LES PROPRIÉTÉS :
- Les propriétés qui deviennent des Link Types ne doivent PAS apparaître comme propriété simple de l'Object Type source
- Si "chef" est détecté comme un lien vers Employé, il ne doit pas apparaître comme propriété STRING de Employé
- Par contre, le côté "many" du link doit avoir une propriété foreign key (ex: "chef_id") pour supporter le lien

TYPES FOUNDRY SUPPORTÉS : STRING, INTEGER, LONG, DOUBLE, BOOLEAN, TIMESTAMP, DATE

RÉPONDS UNIQUEMENT avec ce JSON (pas de markdown, pas de ```):
{{
  "object_types": [
    {{
      "id": "kebab-case-id",
      "display_name": "Nom Affichable",
      "plural_display_name": "Noms Affichables",
      "api_name": "PascalCaseName",
      "description": "Description courte",
      "primary_key": "property_id_de_la_pk",
      "title_property": "property_id_pour_le_titre",
      "properties": [
        {{
          "id": "snake_case_id",
          "display_name": "Nom Affichable",
          "type": "STRING",
          "nullable": false,
          "description": "Description"
        }}
      ],
      "source_columns": ["colonnes_csv_utilisées"]
    }}
  ],
  "link_types": [
    {{
      "id": "kebab-case-link-id",
      "display_name": "Nom du Lien",
      "plural_display_name": "Noms des Liens",
      "api_name": "camelCaseName",
      "from_object": "object-type-id-source",
      "from_property": "pk_property_id_du_source",
      "to_object": "object-type-id-cible",
      "to_property": "fk_property_id_dans_cible",
      "cardinality": "ONE_TO_MANY|MANY_TO_MANY|ONE_TO_ONE",
      "left_to_right_label": "a pour X",
      "right_to_left_label": "appartient à Y",
      "description": "Description de la relation"
    }}
  ],
  "reasoning": "Explication courte de ton raisonnement"
}}"""


def analyze_schema(schema: dict, model: str = "claude-sonnet-4-20250514") -> dict:
    """
    Envoie le schema à Claude API et retourne l'ontologie proposée.

    Args:
        schema: Le schema JSON produit par le parser
        model: Le modèle Claude à utiliser

    Returns:
        L'ontologie proposée en JSON structuré
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY non définie. "
            "Export ta clé : export ANTHROPIC_API_KEY='sk-ant-...'"
        )

    client = Anthropic(api_key=api_key)

    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        schema_json=json.dumps(schema, indent=2, ensure_ascii=False)
    )

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text.strip()

    # Nettoyer si Claude a quand même mis du markdown
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        raw_text = "\n".join(lines)

    try:
        ontology = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Claude a retourné du JSON invalide : {e}\n\nRéponse brute :\n{raw_text}"
        )

    validate_ontology(ontology)
    return ontology


def validate_ontology(ontology: dict) -> None:
    """Validation basique de la structure de l'ontologie."""
    if "object_types" not in ontology:
        raise ValueError("L'ontologie doit contenir 'object_types'")
    if "link_types" not in ontology:
        raise ValueError("L'ontologie doit contenir 'link_types'")

    obj_ids = set()
    for ot in ontology["object_types"]:
        for field in ("id", "display_name", "properties", "primary_key"):
            if field not in ot:
                raise ValueError(f"Object type manque le champ '{field}': {ot}")
        obj_ids.add(ot["id"])

        prop_ids = set()
        for prop in ot["properties"]:
            if "id" not in prop or "type" not in prop:
                raise ValueError(f"Propriété invalide dans {ot['id']}: {prop}")
            prop_ids.add(prop["id"])

        if ot["primary_key"] not in prop_ids:
            raise ValueError(
                f"Primary key '{ot['primary_key']}' introuvable dans les propriétés de {ot['id']}"
            )

    for lt in ontology["link_types"]:
        for field in ("id", "from_object", "to_object", "cardinality"):
            if field not in lt:
                raise ValueError(f"Link type manque le champ '{field}': {lt}")
        if lt["from_object"] not in obj_ids:
            raise ValueError(
                f"Link type '{lt['id']}' référence un object inconnu : {lt['from_object']}"
            )
        if lt["to_object"] not in obj_ids:
            raise ValueError(
                f"Link type '{lt['id']}' référence un object inconnu : {lt['to_object']}"
            )


if __name__ == "__main__":
    import sys
    from parser import parse_csv

    if len(sys.argv) < 2:
        print("Usage: python analyzer.py <chemin_csv>")
        sys.exit(1)

    schema = parse_csv(sys.argv[1])
    ontology = analyze_schema(schema)
    print(json.dumps(ontology, indent=2, ensure_ascii=False))
