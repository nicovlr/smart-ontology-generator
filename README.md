# Smart Ontology Generator

Genere automatiquement des ontologies Palantir Foundry a partir de fichiers CSV.

Analyse semantiquement les donnees via Claude API pour detecter les entites, proprietes et relations, puis cree tout dans Foundry via MCP.

## Ce que ca fait

```
CSV brut  -->  Analyse semantique (Claude)  -->  Ontologie Foundry
                                                  - Object Types
                                                  - Properties
                                                  - Link Types
                                                  - Datasets
```

### Exemple

**Input** : un CSV d'employes
```csv
nom,chef,bureau,projet_en_cours
Alice,Bob,Paris-3A,Refonte API
Bob,,Lyon-1B,Migration DB
```

**Output** : 3 Object Types + 3 Link Types crees dans Foundry
- Employe, Bureau (ville extraite de "Paris-3A"), Projet
- Relations : manage par, travaille dans, assigne a

## Installation

```bash
git clone https://github.com/nicovlr/smart-ontology-generator.git
cd smart-ontology-generator
pip install anthropic
```

## Usage

### Mode schema (sans API key)
```bash
python3 -m ontology_generator.main data.csv --schema-only
```

### Mode complet
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python3 -m ontology_generator.main data.csv --auto-approve --prepare-foundry
```

### Mode Claude Code (recommande)
Pas besoin d'API key. Ouvrez Claude Code dans ce dossier et demandez :
```
Analyse sample_data/employes.csv et cree l'ontologie dans Foundry
```

## Architecture

```
ontology_generator/
  parser.py           # Module 1 : Parse CSV -> schema JSON
  analyzer.py         # Module 2 : Claude API -> ontologie proposee
  formatter.py        # Module 3 : Affichage lisible
  foundry_creator.py  # Module 4 : Generation CSV + plan MCP
  main.py             # CLI orchestrateur
```

## Connexion Palantir Foundry

Configurer le MCP Palantir :
```bash
export FOUNDRY_HOST="xxx.palantirfoundry.com"
export FOUNDRY_TOKEN="votre-token"
claude mcp add palantir-mcp --scope project \
  -e FOUNDRY_TOKEN=$FOUNDRY_TOKEN \
  -- npx -y palantir-mcp --foundry-api-url "https://$FOUNDRY_HOST"
```

## Licence

MIT
