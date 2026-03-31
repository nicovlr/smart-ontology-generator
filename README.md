# Smart Ontology Generator

Automatically generate Palantir Foundry ontologies from CSV files.

Semantically analyzes data via Claude API to detect entities, properties and relationships, then creates everything in Foundry via MCP.

## What it does

```
Raw CSV  -->  Semantic Analysis (Claude)  -->  Foundry Ontology
                                                - Object Types
                                                - Properties
                                                - Link Types
                                                - Datasets
```

### Example

**Input**: an employee CSV
```csv
name,manager,office,current_project
Alice,Bob,Paris-3A,API Refactor
Bob,,Lyon-1B,DB Migration
```

**Output**: 3 Object Types + 3 Link Types created in Foundry
- Employee, Office (city extracted from "Paris-3A"), Project
- Relations: managed by, works in, assigned to

## Installation

```bash
git clone https://github.com/nicovlr/smart-ontology-generator.git
cd smart-ontology-generator
pip install anthropic
```

## Usage

### Schema-only mode (no API key needed)
```bash
python3 -m ontology_generator.main data.csv --schema-only
```

### Full mode
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python3 -m ontology_generator.main data.csv --auto-approve --prepare-foundry
```

### Claude Code mode (recommended)
No API key needed. Open Claude Code in this folder and ask:
```
Analyze sample_data/employes.csv and create the ontology in Foundry
```

## Architecture

```
ontology_generator/
  parser.py           # Module 1: Parse CSV -> JSON schema
  analyzer.py         # Module 2: Claude API -> proposed ontology
  formatter.py        # Module 3: Human-readable display
  foundry_creator.py  # Module 4: CSV generation + MCP execution plan
  main.py             # CLI orchestrator
```

## Connecting to Palantir Foundry

Configure the Palantir MCP server:
```bash
export FOUNDRY_HOST="your-instance.palantirfoundry.com"
export FOUNDRY_TOKEN="your-token"
claude mcp add palantir-mcp --scope project \
  -e FOUNDRY_TOKEN=$FOUNDRY_TOKEN \
  -- npx -y palantir-mcp --foundry-api-url "https://$FOUNDRY_HOST"
```

## Example: Nexus (Unified Brain)

The `examples/nexus/` folder contains a real-world example: **Nexus**, a system that connects multiple MCP services (Jira, Gmail, Calendar, Figma) into a single Foundry ontology graph.

### Nexus Architecture

```
User ("sync" / "brief")
        |
        v
     Claude (orchestrator)
   /    |    |    \     \
Jira  Gmail  Cal  Figma  GitHub
   \    |    |    /     /
        v
  Palantir Foundry
  (7 Object Types + 12 Link Types)
```

### Nexus Ontology

| Object Type | Description |
|---|---|
| Project | Software or academic project |
| Task | Jira ticket or manual task |
| Email | Important indexed email |
| Event | Calendar event |
| Skill | Technology or competency |
| Deadline | Important due date |
| Design | Figma file or component |

12 Link Types connect everything: tasks belong to projects, emails concern projects, skills are used by projects, deadlines require skills, tasks block other tasks, etc.

See `examples/nexus/ontology_schema.json` for the full schema.

### Nexus Commands (when deployed)

| Command | What Claude does |
|---|---|
| `sync` | Update Foundry from all connected MCPs |
| `brief` | Generate weekly summary |
| `status <project>` | Detailed project status |
| `week` | Show week (events + deadlines + tasks) |
| `retro <month>` | Monthly retrospective |

## License

MIT
