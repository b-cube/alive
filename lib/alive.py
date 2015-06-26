#!/usr/bin/env python

from rdflib import Graph, Namespace, URIRef
from rdflib.plugins.stores import sparqlstore
from rdflib.namespace import DCTERMS
import requests
import os
import time
import concurrent.futures as futures
import logging

logging.basicConfig(filename="alive.log", level=logging.DEBUG)
logger = logging.getLogger(__name__)

__location__ = os.path.realpath(
               os.path.join(os.getcwd(), os.path.dirname(__file__)))


class Store():
    '''
    This class is a wrapper for the Graph class that
    handles ontology binding and triples serialization.
    '''

    def __init__(self, endpoint=None):
        if endpoint is None:
            self.g = Graph()
        else:
            self._store = sparqlstore.SPARQLUpdateStore(endpoint, endpoint)
            # self._store.open((endpoint, endpoint))
            self.g = Graph(self._store, URIRef('urn:x-arq:DefaultGraph'))
        self.ns = {}

    def bind_namespaces(self, namespaces):
        for ns in namespaces:
            # ns is the prefix and the key
            self.g.bind(ns, Namespace(namespaces[ns]))
            self.ns[ns] = Namespace(namespaces[ns])

    def get_namespaces(self):
        ns = []
        for namespace in self.g.namespaces():
            ns.append(namespace)
        return ns

    def serialize(self, format):
        return self.g.serialize(format=format)

    def update(self, query):
        return self.g.update(query)

    def query(self, query):
        return self.g.query(query)


class Alive():
    '''
    This class will update triples based on url availability
    '''
    def __init__(self, endpoint):
        self.counter = 0
        self.status = []
        self.urls = []
        self.store = Store(endpoint)
        ontology_uris = {
            'wso': 'http://purl.org/nsidc/bcube/web-services#',
            'dc': str(DCTERMS)
        }
        self.store.bind_namespaces(ontology_uris)
        qres = self.store.query("""SELECT  DISTINCT ?base_url
                        WHERE {
                                ?subject wso:BaseURL ?base_url .
                        }
                        """)
        for row in qres:
            self.urls.append(str(row[0].n3()[1:-1]))

    def get_urls(self):
        return self.urls

    def url_status(self):
        return self.status

    def fetch_url(self, url):
        try:
            status = requests.head(url).status_code
        except:
            status = 500
        status_tuple = (url, status)
        self.status.append(status_tuple)
        return status

    def update_url_status(self, url, status):
        '''
        This class updates a triple refering to a URL on when was the last time
        that returned a 200 or 400, both indicate that the service is there.

        Note: There should be a way to update the triples using multithreading.
        '''
        try:
            date = time.strftime("%d/%m/%Y")
            if status in [200, 400]:
                sparql_update_query = """
                    DELETE
                    {
                        ?s ?p ?o
                    }
                    WHERE
                    {
                        ?s wso:BaseURL \"""" + url + """\" .
                        ?s wso:alive ?o .
                        ?s ?p ?o .
                    }

                    INSERT
                    {
                        ?subject wso:alive \"""" + date + """\" .
                    }
                    WHERE
                    {
                        ?subject wso:BaseURL \"""" + url + """\" .
                    }"""
                print url
                self.store.update(sparql_update_query)
                self.counter += 1
        except Exception as e:
            print type(e)
            return None

    def populate(self):
        '''
        Populates an array of tuples (url, request_status_code) using
        multithreading requests.
        The input URLs array comes from the initial SPARQL query.
        '''
        with futures.ThreadPoolExecutor(max_workers=8) as executor:
            workload = executor.map(self.fetch_url, self.get_urls())

    def update(self):
        '''
        Updates the "alive!" status of the URLs with 200 or 400 response codes.
        '''
        for url, status in self.url_status():
            self.update_url_status(url, status)


def main():
    alive = Alive("http://54.69.87.196:8080/parliament/sparql")
    alive.populate()
    print "Updating: " + str(len(alive.get_urls())) + " URLs"
    alive.update()
    print "Updated: " + str(alive.counter) + " URLs as alive!"


if __name__ == '__main__':
    main()
