#!/usr/bin/env python

from rdflib import Graph, Namespace, URIRef
from rdflib.plugins.stores import sparqlstore
from rdflib.namespace import DCTERMS
from datetime import timedelta
from optparse import OptionParser
import requests
import time
import concurrent.futures as futures
import logging


logging.basicConfig(filename="alive.log", level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARN)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.addHandler(console)


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
        self.timeout = 1
        self.status = []
        self.urls = []
        self.response_counts = {}
        self.store = Store(endpoint)
        ontology_uris = {
            'wso': 'http://purl.org/nsidc/bcube/web-services#',
            'prov': 'http://www.w3.org/ns/prov#',
            'vcard': 'http://www.w3.org/TR/vcard-rdf/#',
            'http': 'http://www.w3.org/2011/http#',
            'dc': str(DCTERMS)
        }
        self.store.bind_namespaces(ontology_uris)
        start = time.time()
        qres = self.store.query("""SELECT  DISTINCT ?base_url
                        WHERE {
                                ?subject vcard:hasURL ?base_url .
                                FILTER regex(?base_url, "noaa", "i")
                        }
                        """)
        end = time.time()
        elapsed = end - start
        logger.info(
            "The Sparql endpoint returned {0} URLs, query time: {1}".format(
                str(len(qres)),
                str(timedelta(seconds=elapsed)))
        )
        for row in qres:
            self.urls.append(str(row[0].n3()[1:-1]))
        qres = None

    def get_urls(self):
        return self.urls

    def url_status(self):
        return self.status

    def fetch_url(self, url):
        try:
            status = requests.head(url, timeout=self.timeout).status_code
        except Exception:
            status = 500
        status_tuple = (url, status)
        # This is 'thread-safe' thanks to the Python GIL
        self.status.append(status_tuple)
        if str(status) in self.response_counts:
            self.response_counts[str(status)] += 1
        else:
            self.response_counts[str(status)] = 1
        logger.debug("Appended: " + url + " with response code: " + str(status))
        return status

    def delete_response_triples(self):
        '''
        Deletes all the triples related to the last time the URLs were checked.
        :return: None
        '''
        try:
            date = time.strftime("%Y-%m-%d")
            sparql_delete_query = """
                DELETE
                {
                ?s ?p ?o
                }
                WHERE
                {
                ?s prov:atTime ?o .
                ?s ?p ?o .
                };

                DELETE
                {
                ?s ?p ?o
                }
                WHERE
                {
                ?s http:statusCodeValue ?o .
                ?s ?p ?o .
                };
            """
            logger.info("Deleting response triples")
            self.store.update(sparql_delete_query)
        except Exception as e:
            logger.error(type(e) + " ERROR DELETING RESPONSE TRIPLES")
            return None


    def update_statuses(self, sparql_update_query):
        '''
        This class updates a triple refering to a URL on when was the last time
        that returned a 200 or 400, both indicate that the service is there.

        Note: There should be a way to update the triples using multithreading.
        '''
        try:
            self.store.update(sparql_update_query)
        except Exception as e:
            logger.error(type(e) + " ERROR INSERTING RESPONSE TRIPLES")
            return None

    def populate(self, fetcher_threads, timeout):
        '''
        Populates an array of tuples (url, request_status_code) using
        multithreading requests.
        The input URLs array comes from the initial SPARQL query.
        '''
        self.timeout = timeout
        with futures.ThreadPoolExecutor(max_workers=fetcher_threads) as executor:
            workload = executor.map(self.fetch_url, self.get_urls())
        return workload

    def update(self):
        '''
        Updates the status of the URLs with the latest HTTP response code.
        '''
        sparql_update_query = ""
        date = time.strftime("%Y-%m-%d")
        for i in range(0, len(self.url_status()), 100):
            template = """
                INSERT
                {
                    ?subject prov:atTime \"%s\"^^xsd:date .
                    ?subject http:statusCodeValue \"%s\"^^xsd:integer .
                }
                WHERE
                {
                    ?subject vcard:hasURL \"%s\" .
                };"""

            paginated_update = "\n".join([template % (date, v, k) for (k, v) in self.url_status()[i:i + 100]])
            self.update_statuses(paginated_update)


def main():
    p = OptionParser()
    p.add_option('--sparql', '-s', help='The Sparql endpoint we want to update')
    p.add_option('--workers', '-w', help='Number of threads used to check the URLs status', default=8, type="int")
    p.add_option('--timeout', '-t', help='Number of seconds to wait for an HTTP response', default=1, type="int")
    p.add_option('--verbose', '-v', help='Increases the output verbosity', action='store_true')
    options, arguments = p.parse_args()

    total_start = time.time()

    if options.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if options.sparql is None:
        print ("Missing SPARQL endpoint")
        p.print_help()
        exit(1)

    if options.workers is None:
        threads = 8
    else:
        threads = options.workers
        if threads > 256:
            threads = 256  # sanity check!

    timeout = options.timeout
    if timeout > 10:
        timeout = 10  # if the timeout is more than 10 seconds this will never end.

    alive = Alive(options.sparql)
    if len(alive.urls) > 1:
        start = time.time()
        alive.populate(threads, timeout)
        end = time.time()
        elapsed = end - start
        msg = "Checked {0} URLs, elapsed time: {1}".format(
            str(len(alive.get_urls())),
            str(timedelta(seconds=elapsed))
        )
        logger.info(msg)
        counts = ["URLs that responded HTTP %s: %s" % (k, v) for (k, v) in alive.response_counts.iteritems()]
        for response in counts:
            logger.info(response)
        alive.delete_response_triples()
        start = time.time()
        alive.update()
        end = time.time()
        elapsed = end - start
        msg = "Triple store updated, update query time: " + str(timedelta(seconds=elapsed))
        logger.info(msg)
    else:
        msg = "No URLs were returned by the sparql endpoint"
        logger.info(msg)
    total_end = time.time()
    total_elapsed = total_end - total_start
    logger.info("Total elapsed time: " + str(timedelta(seconds=total_elapsed)))


if __name__ == '__main__':
    main()
