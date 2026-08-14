# Private registry boundary

**Do not commit PII here.** This public repository must never contain raw lead/customer records, phone/email subscriber databases, consent ledgers, order exports, payment data, analytics identifiers, or private Chronos receipts.

The canonical private implementation should live behind authenticated infrastructure and persist at minimum:

- contact/subject identifier
- consent channel and exact consent-text version
- grant/revoke timestamp
- acquisition source
- immutable event/receipt ID
- provenance and integrity hash

`registry/contracts/lead-ingest.schema.json` and `registry/schema/consent.schema.json` define the public contracts without exposing the private records.
