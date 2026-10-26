---
name: api-design
description: "Design and review API contracts. Use when adding or changing an endpoint, a schema, or a client integration."
triggers:
- api
- rest
- endpoint
- contract
- schema
- graphql
- payload
---

# API Design

- Validate all inputs at the boundary; reject unknown fields.
- Use consistent naming, status codes, and error shapes across the surface.
- Make changes backward compatible; version or deprecate instead of breaking.
- Design for idempotency on retried writes.
- Document each endpoint with an example request and response.
