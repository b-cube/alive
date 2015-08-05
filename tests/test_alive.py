#!/usr/bin/env python

import unittest
from app.alive import Alive


class Response:
    def __init__(self):
        self.status_code = 0
        self.history = []
        self.url = ''
        self.reason = ''
        self.elapsed = lambda: None
        setattr(self.elapsed, 'microseconds', '1000')


class TestAlive(unittest.TestCase):
    '''
    TODO: mock SPARQL results
    '''

    def mock_response_object(self, status_code, status_message):
        r = Response()
        r.status_code = status_code
        r.reason = status_message
        return r

    @unittest.skip("skipping SPARQL query test")
    def test_load_all_urls(self):
        alive = Alive(None)
        query = """
                SELECT  DISTINCT ?base_url
                WHERE {
                    ?subject vcard:hasURL ?base_url .
                }
                """
        alive.load_urls(query)
        self.assertTrue(len(alive.get_urls()) > 0)

    def test_response_builder_200(self):
        alive = Alive(None)  # we don't need an sparql endpoint
        r = self.mock_response_object(200, 'doo')
        json_response = alive.build_json_response(r, 'http://foo')

        self.assertEquals(json_response['status_code'], 200)
        self.assertEquals(json_response['status_family'], 'Success message')
        self.assertEquals(json_response['status_message'], 'doo')
        self.assertEquals(json_response['url'], 'http://foo')

    def test_response_builder_300_moved(self):
        alive = Alive(None)  # we don't need an sparql endpoint
        r = self.mock_response_object(301, 'baz')
        json_response = alive.build_json_response(r, 'http://moved')

        self.assertEquals(json_response['status_code'], 301)
        self.assertEquals(json_response['status_family'], 'Redirected message')
        self.assertEquals(json_response['status_message'], 'baz')
        self.assertEquals(json_response['url'], 'http://moved')
        self.assertEquals(json_response['redirect_url'], '')

    def test_response_builder_300_redirect(self):
        alive = Alive(None)  # we don't need an sparql endpoint
        r = self.mock_response_object(301, 'baz')
        r.history = ['301']
        r.url = 'http://new-url'
        json_response = alive.build_json_response(r, 'http://moved')

        self.assertEquals(json_response['status_code'], 301)
        self.assertEquals(json_response['status_family'], 'Redirected message')
        self.assertEquals(json_response['status_message'], 'baz')
        self.assertEquals(json_response['url'], 'http://moved')
        self.assertEquals(json_response['redirect_url'], 'http://new-url')

    def test_response_builder_400(self):
        alive = Alive(None)  # we don't need an sparql endpoint
        r = self.mock_response_object(404, 'moo')
        json_response = alive.build_json_response(r, 'http://notfound')

        self.assertEquals(json_response['status_code'], 404)
        self.assertEquals(json_response['status_family'], 'Client error')
        self.assertEquals(json_response['status_message'], 'moo')
        self.assertEquals(json_response['url'], 'http://notfound')
        self.assertEquals(json_response['redirect_url'], '')


    def test_response_builder_500(self):
        alive = Alive(None)  # we don't need an sparql endpoint
        r = self.mock_response_object(500, 'doo')
        json_response = alive.build_json_response(r, 'http://foo')

        self.assertEquals(json_response['status_code'], 500)
        self.assertEquals(json_response['status_family'], 'Server error')
        self.assertEquals(json_response['status_message'], 'doo')
        self.assertEquals(json_response['url'], 'http://foo')
