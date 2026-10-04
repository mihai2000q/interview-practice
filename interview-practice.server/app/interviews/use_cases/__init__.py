"""One module per use case of the interviews API.

A use case holds the whole logic of an endpoint (loading, rules, LLM calls, storing,
committing) and returns domain objects. The routes only parse the request, call a use
case and build the response.
"""
