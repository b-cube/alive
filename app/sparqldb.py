#!/usr/bin/env python

from SPARQLWrapper import SPARQLWrapper, JSON
import sys


class SparqlDB:
    """
    This class handles ontology binding and triples serialization.
    """

    def __init__(self, endpoint=None):
        """
        :param endpoint: a valid sparql endpoint
        :return: None
        """
        self._credentials = None  # Auth
        self._prefixes = {}  # these will be used to store prefixes
        self._prefixes_query = ""  # the actual string used in the queries
        self._timeout = 5  # seconds
        self._sparql = SPARQLWrapper(endpoint)
        self._sparql.setReturnFormat(JSON)
        self._sparql.setTimeout(self._timeout)



    def set_credentials(self, user, password):
        """
        :param user: username
        :param password: password
        :return: None
        """
        self.credentials = (user, password)
        self.sparql.setCredentials(user, password)
        return None

    def set_timeout(self, timeout):
        """
        :param timeout: seconds
        :return: None
        """
        self._sparql.setTimeout(timeout)
        self._timeout = timeout

    def add_prefix(self, prefix, namespace):
        """
        :param prefix: a prefix for a namespace i.e. in dc:terms dc is the prefix
        :param namespace: the full URI for a namespace i.e. http://purl.org/something#
        :return: None
        """
        if prefix not in self._prefixes:
            self._prefixes[prefix] = namespace
        self._build_prefixes()
        return None

    def _build_prefixes(self):
        """
        Creates a concatenated string with all the prefixes.
        :return: None
        """
        self._prefixes_query = "\n".join(["PREFIX %s: <%s>" % (k, v) for (k, v) in self._prefixes.items()])
        return None

    def query(self, sparql_query):
        """
        :param sparql_query: a valid sparql string query
        :return: an dict with the SPARQL results or None if there is an exception
        """
        query = self._prefixes_query + "\n" + sparql_query
        self._sparql.setQuery(query)
        try:
            res = self._sparql.query().convert()
            result = res["results"]
        except Exception:
            e = sys.exc_info()[1]
            print(e)
            result = None
        return result