# Captain Voice Assistant Backend

This backend package is organized around a hexagonal architecture with domain, application, adapters, and configuration layers.

## Structure

- `domain/` for entities, value objects, and domain events
- `application/` for commands, queries, and ports
- `adapters/` for inbound and outbound integrations
- `config/` for settings and dependency injection
- `tests/` for unit, integration, and end-to-end coverage
