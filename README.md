# abstract-wiki-schemata-generator
OpenAPI Schema Generation for Abstract Wikipedia/Wikifunctions/Wikilambda

## Usage
python generate.py [--form=<NORMAL|CANONICAL>] [command]

### Commands

#### list

Lists all ZIDs for which a schema can be generated with the given form.

#### generate

Generates an OpenAPI schema for a given ZID.

Arguments:
- `root_directory` (string): where to save the generated .yaml files
- `tag` (string): tag to be used to generates unique IDs for schemata. IDs are of the form `tag`/`ZID`
- `ZID` (string): ZID for which to generate the schema
- `dry_run` (bool): if true, prints to stdout; if false, write to `root_directory`/`ZID`.yaml
