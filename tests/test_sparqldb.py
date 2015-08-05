#!/usr/bin/env python

from app.sparqldb import SparqlDB
import unittest
import threading


class TestBasicCases(unittest.TestCase):
    def setUp(self):
        self.conn = SparqlDB('http://dbpedia.org/sparql')

    def tearDown(self):
        self.conn._prefixes = {}

    def test_basic_query(self):
        """
        initial test. ensure that we can connect to the dbpedia sparql endpoint
        for testing and do a simple query with custom ontology binding.
        """
        self.assertEquals(isinstance(self.conn, SparqlDB), True)
        self.conn.add_prefix("rdfs", "http://www.w3.org/2000/01/rdf-schema#")
        self.assertEquals(self.conn._prefixes_query,
                          "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>")
        query = """SELECT ?label
                    WHERE { <http://dbpedia.org/resource/Boulder> rdfs:label ?label }
                """
        res = self.conn.query(query)
        self.assertIsNotNone(res)
        self.assertTrue(isinstance(res, dict))
        for result in res["bindings"]:
            if result['label']['xml:lang'] == 'en':
                self.assertEquals(result['label']['value'], 'Boulder')
            if result['label']['xml:lang'] == 'es':
                self.assertEquals(result['label']['value'], 'Bloque (roca)')

    def test_other_query(self):
        """
        tests that we can do more complicated queries, this time using the
        built-in ontologies from dbpedia: http://dbpedia-live.openlinksw.com/sparql?nsdecl
        """
        # Bands from Denver, why not!
        query = """SELECT ?name ?place
                    WHERE {
                        ?place rdfs:label "Denver"@en .
                        ?band dbo:hometown ?place .
                        ?band rdf:type dbo:Band .
                        ?band rdfs:label ?name .
                        FILTER langMatches(lang(?name),'en')
                    }
                """
        res = self.conn.query(query)
        self.assertIsNotNone(res)
        bands = []
        for result in res["bindings"]:
            bands.append(result['name']['value'])

        self.assertTrue("DeVotchKa" in bands)
        self.assertTrue("Flobots" in bands)
        self.assertTrue("The Lumineers" in bands)

    def test_multiple_users(self):
        """
        tests that we can send multiple concurrent
        requests to the sparql endpoint
        """
        results = []

        def user(query):
            result = self.conn.query(query)
            if result is not None:
                results.append((result['bindings'][0], query))

        queries = ["""SELECT ?label
                    WHERE {
                    <http://dbpedia.org/resource/Boulder> rdfs:label ?label
                    FILTER langMatches(lang(?label),'en') }
                  """,
                   """SELECT DISTINCT count (?res) as ?count
                    WHERE {
                    ?res geo:lat ?v. }
                  """,
                   """SELECT ?country
                    WHERE{
                    ?country dct:subject <http://dbpedia.org/resource/Category:Countries_in_Europe>
                    }
                  """
                   ]
        users = []
        for i in range(3):
            t = threading.Thread(target=user, args=(queries[i],))
            users.append(t)
            t.start()
        for t in users:
            t.join()

        # when we get the results we assert that they came from the proper query
        for result, query in results:
            if 'label' in result:
                self.assertTrue(query == queries[0])
            if 'count' in result:
                self.assertTrue(query == queries[1])
            if 'country' in result:
                self.assertTrue(query == queries[2])

