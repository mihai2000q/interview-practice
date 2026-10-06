"""One module (or package, once it grows) per use case of the documents API.

A use case holds the whole logic of an endpoint and returns domain objects; the routes
only parse the request, call a use case and build the response.
"""
