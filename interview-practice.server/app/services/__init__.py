"""Capabilities used by more than one domain.

A service is a stateless operation that belongs to no single use case. It may depend on
`models`, `llm` and `errors`, never on a domain or a use case; domains depend on
services. Keep it for what is shared across domains and give each module a specific
name.
"""
