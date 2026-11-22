"""Gzip for API responses, when the client sends Accept-Encoding: gzip.

GET /tickets with 1,000 tickets is about 1.7 MB of JSON and compresses to about 80 KB,
in about 7 ms. Clients that don't ask for gzip get the same bytes as before.

Console pages and their static files are never compressed. A console page can carry a
CSRF token and reporter details next to text from the URL (a search, say), which is the
shape a BREACH attack needs; Django masks CSRF tokens and adds random bytes to each gzip
header, but the console gains little from compression, so it stays out. WhiteNoise
already serves precompressed static files on its own. API responses are safe to
compress: the bearer token is never echoed, and browsers never attach it on their own,
so a third-party page can't make a victim's browser send authenticated API requests.
"""

from django.middleware.gzip import GZipMiddleware

from cra_service.middleware import _is_console


class ApiGZipMiddleware(GZipMiddleware):
    def process_response(self, request, response):
        if _is_console(request.path_info):
            return response
        return super().process_response(request, response)
