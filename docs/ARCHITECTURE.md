# Architecture

The lab separates a **happy-path validity check** from an **independent intent oracle**.

## Happy-path layer

Each fixture names one surface field that a naive check would use:

- Tesla analog: `product_name == FSD`
- SpaceX analog: `service_name == AviationLink`
- xAI analog: `assistant_name == Grok`

The mutant keeps that field unchanged and remains valid YAML. That is the analog of “the document still deploys.”

## Intent layer

`policies/*.json` freeze a human-readable claim in machine-readable form. `tools/drift_lab.py` then:

1. Reads the artifact with a tiny stdlib YAML subset parser.
2. Extracts only the paths named by the primary rule and supporting rules.
3. Compares observed values to frozen intent.
4. Generates boundary cases from the contract.
5. Issues GO only when every rule matches.
6. Writes JSON and HTML evidence.

The artifact does not grade itself. The contract is the oracle.

## Rule kinds

v1 supports three narrow kinds:

- `required_enum` — string must equal `expected` and must not appear in `forbidden`
- `numeric_threshold` — number must satisfy `>=` or `<=`
- `required_flag` — boolean must equal `expected`

Unknown kinds, missing files, missing paths, and non-numeric thresholds are hard failures (exit 1). They never become GO.

## Why mutation is part of the demo

`mutations/` contains documents that still look like the original product surface. The name did not change. The parser still works. The operating rule did.

## Production evolution

A later lab could add live official-post intake, research-swarm source gathering, NAT scans of an analog OpenAPI, and Grok-drafted report prose. None of those own the decision bit.
