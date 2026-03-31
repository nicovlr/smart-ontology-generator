"""
Module 3 : Formatter d'affichage
Formate l'ontologie proposée en texte lisible pour validation utilisateur.
"""


ICONS = {
    "object": "[OBJ]",
    "property": "  |--",
    "pk": "  |** PK",
    "link": "[LNK]",
}


def format_ontology(ontology: dict) -> str:
    """Formate l'ontologie en texte clair pour la console."""
    lines: list[str] = []

    lines.append("=" * 60)
    lines.append("  ONTOLOGIE PROPOSÉE")
    lines.append("=" * 60)

    # Object Types
    lines.append("")
    lines.append(f"  {len(ontology['object_types'])} Object Type(s) détecté(s)")
    lines.append("-" * 60)

    for ot in ontology["object_types"]:
        lines.append("")
        lines.append(f"{ICONS['object']} {ot['display_name']} ({ot['id']})")
        if ot.get("description"):
            lines.append(f"      {ot['description']}")
        lines.append(f"      API: {ot.get('api_name', 'N/A')} | PK: {ot['primary_key']}")

        for prop in ot["properties"]:
            is_pk = prop["id"] == ot["primary_key"]
            icon = ICONS["pk"] if is_pk else ICONS["property"]
            nullable = "?" if prop.get("nullable", False) else ""
            desc = f"  -- {prop.get('description', '')}" if prop.get("description") else ""
            lines.append(f"{icon} {prop['id']}: {prop['type']}{nullable}{desc}")

    # Link Types
    lines.append("")
    lines.append(f"  {len(ontology['link_types'])} Link Type(s) détecté(s)")
    lines.append("-" * 60)

    for lt in ontology["link_types"]:
        lines.append("")
        card = lt["cardinality"]
        card_symbol = {"ONE_TO_MANY": "1──n", "MANY_TO_MANY": "n──n", "ONE_TO_ONE": "1──1"}.get(card, card)

        lines.append(f"{ICONS['link']} {lt['display_name']} ({lt['id']})")
        lines.append(f"      {lt['from_object']} ──({card_symbol})──> {lt['to_object']}")

        if lt.get("left_to_right_label"):
            lines.append(f"      → {lt['left_to_right_label']}")
        if lt.get("right_to_left_label"):
            lines.append(f"      ← {lt['right_to_left_label']}")
        if lt.get("description"):
            lines.append(f"      {lt['description']}")

    # Reasoning
    if ontology.get("reasoning"):
        lines.append("")
        lines.append("-" * 60)
        lines.append("  Raisonnement :")
        lines.append(f"  {ontology['reasoning']}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def format_ontology_summary(ontology: dict) -> str:
    """Résumé court de l'ontologie (pour logs ou confirmations)."""
    n_obj = len(ontology["object_types"])
    n_link = len(ontology["link_types"])
    obj_names = ", ".join(ot["display_name"] for ot in ontology["object_types"])
    return f"{n_obj} object type(s) [{obj_names}] + {n_link} link type(s)"


def format_diff(old_ontology: dict, new_ontology: dict) -> str:
    """Affiche les différences entre deux versions d'ontologie."""
    lines: list[str] = []

    old_obj_ids = {ot["id"] for ot in old_ontology["object_types"]}
    new_obj_ids = {ot["id"] for ot in new_ontology["object_types"]}

    added = new_obj_ids - old_obj_ids
    removed = old_obj_ids - new_obj_ids

    if added:
        lines.append(f"  + Object types ajoutés : {', '.join(added)}")
    if removed:
        lines.append(f"  - Object types supprimés : {', '.join(removed)}")

    old_link_ids = {lt["id"] for lt in old_ontology["link_types"]}
    new_link_ids = {lt["id"] for lt in new_ontology["link_types"]}

    added_links = new_link_ids - old_link_ids
    removed_links = old_link_ids - new_link_ids

    if added_links:
        lines.append(f"  + Link types ajoutés : {', '.join(added_links)}")
    if removed_links:
        lines.append(f"  - Link types supprimés : {', '.join(removed_links)}")

    if not lines:
        lines.append("  Aucun changement détecté.")

    return "\n".join(lines)


if __name__ == "__main__":
    # Test avec un exemple hardcodé
    sample = {
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
                    {"id": "nom", "display_name": "Nom", "type": "STRING", "nullable": False, "description": "Nom de l'employé"},
                ],
                "source_columns": ["nom"],
            },
            {
                "id": "bureau",
                "display_name": "Bureau",
                "plural_display_name": "Bureaux",
                "api_name": "Bureau",
                "description": "Lieu de travail physique",
                "primary_key": "code",
                "title_property": "code",
                "properties": [
                    {"id": "code", "display_name": "Code", "type": "STRING", "nullable": False, "description": "Code du bureau"},
                    {"id": "ville", "display_name": "Ville", "type": "STRING", "nullable": False, "description": "Ville"},
                ],
                "source_columns": ["bureau"],
            },
            {
                "id": "projet",
                "display_name": "Projet",
                "plural_display_name": "Projets",
                "api_name": "Projet",
                "description": "Projet en cours",
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
                "to_object": "employe",
                "cardinality": "ONE_TO_MANY",
                "left_to_right_label": "manage",
                "right_to_left_label": "est managé par",
                "description": "Relation hiérarchique manager-subordonné",
            },
            {
                "id": "employe-travaille-dans-bureau",
                "display_name": "Travaille dans",
                "plural_display_name": "Travaillent dans",
                "api_name": "travailleDans",
                "from_object": "bureau",
                "to_object": "employe",
                "cardinality": "ONE_TO_MANY",
                "left_to_right_label": "a pour employés",
                "right_to_left_label": "travaille dans",
                "description": "Affectation d'un employé à un bureau",
            },
            {
                "id": "employe-assigne-a-projet",
                "display_name": "Assigné à",
                "plural_display_name": "Assignés à",
                "api_name": "assigneA",
                "from_object": "projet",
                "to_object": "employe",
                "cardinality": "ONE_TO_MANY",
                "left_to_right_label": "a pour employés",
                "right_to_left_label": "est assigné à",
                "description": "Assignation d'un employé à un projet",
            },
        ],
        "reasoning": "Le CSV contient des employés avec relations hiérarchiques (chef), des bureaux avec pattern Ville-Code, et des projets partagés.",
    }

    print(format_ontology(sample))
    print()
    print("Résumé:", format_ontology_summary(sample))
