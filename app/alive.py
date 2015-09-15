#!/usr/bin/env python

from datetime import timedelta
from optparse import OptionParser
import requests
import time
import datetime
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


class Alive():
    '''
    Loads all the URLs from a triples store where the URL
    is part of vcard:hasURL and creates a JSON object
    with all the response codes returned from these URLs
    '''

    def __init__(self, endpoint):
        """
        :param endpoint: Sparql endpoint
        :return: Alive class instance
        """
        self.timeout = 1  # in seconds for the requests
        self.endpoint = endpoint
        self.status = []
        self.urls = []
        self.response_counts = {}
        self.status_family = {
            '100': 'Informational message',
            '200': 'Success message',
            '300': 'Redirected message',
            '400': 'Client error',
            '500': 'Server error'
        }

    def load_urls(self):
        try:
            page = 0
            start = time.time()
            while (True):
                page += 1
                req_url = self.endpoint + '/p/{0}'.format(page)
                qres = requests.get(req_url)
                data = qres.json()
                if len(data['urls']) <= 0:
                    break
                for row in data['urls']:
                    # do we really need unicode?
                    self.urls.append(str(row['base_url']['value']))
            end = time.time()
            elapsed = end - start
        except RuntimeError:
            logger.error("The URLs couldn't be loaded")
            return None

        logger.info(
            "The Sparql endpoint returned {0} URLs, query time: {1}".format(
                str(len(self.urls)),
                str(timedelta(seconds=elapsed)))
        )

    def get_urls(self):
        return self.urls

    def url_status(self):
        return self.status

    def build_error_response(self, url, error):
        r = {
            'url': url,
            'checked_on': datetime.datetime.now().isoformat(),
            'status_code': 408,
            'status_message': 'ERROR',
            'status_family_type': 'Client error',
            'status_family_code': 400,
            'response_time': '0',
            'redirect_url': '',
            'error': error
        }
        return r

    def build_json_response(self, response, url):
        status_family_code = response.status_code
        status_family_code -= status_family_code % 100
        status_family_type = self.status_family[str(status_family_code)]
        if len(response.history) > 0:
            current_url = response.url
        else:
            current_url = ''

        r = {
            'url': url,
            'checked_on': datetime.datetime.now().isoformat(),
            'status_code': response.status_code,
            'status_message': response.reason,
            'status_family_type': status_family_type,
            'status_family_code': status_family_code,
            'response_time': response.elapsed.microseconds,
            'redirect_url': current_url,
            'error': ''
        }
        return r

    def fetch_url(self, url):
        try:
            response = requests.head(url, timeout=self.timeout)
            status = response.reason.upper()
            res = self.build_json_response(response, url)
        except Exception, e:
            res = self.build_error_response(url, str(e))
            status = 'TIMED OUT'
        # This is thread-safe thanks to the Python GIL
        self.status.append(res)
        if status == '':
            status = 'EMPTY RESPONSE'
        if str(status) in self.response_counts:
            self.response_counts[str(status)] += 1
        else:
            self.response_counts[str(status)] = 1
        logger.debug("Appended: " + url + " with response code: " + str(status))
        return res

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

    def update_urls(self):
        """
        This method updates the status of the URLs in the triple store
        :return: 200 if successful
        """
        post_res = requests.post(self.endpoint, json=self.status)
        logger.debug("Updated URLS with response code: " + str(post_res.status_code))


def main():
    p = OptionParser()
    p.add_option('--api', '-a', help='REST endpoint, this is where the URLs statuses are updated in the triple store')
    p.add_option('--workers', '-w', help='Number of threads used to check the URLs status', default=8, type="int")
    p.add_option('--timeout', '-t', help='Number of seconds to wait for an HTTP response', default=1, type="int")
    p.add_option('--verbose', '-v', help='Increases the output verbosity', action='store_true')
    options, arguments = p.parse_args()

    total_start = time.time()

    if options.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if options.api is None:
        print ("Missing BCube REST endpoint")
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

    alive = Alive(options.api)
    alive.load_urls()
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
        alive.update_urls()
        counts = ["URLs with HTTP status (%s): %s" % (k, v) for (k, v) in alive.response_counts.iteritems()]
        for response in counts:
            logger.info(response)
    else:
        msg = "No URLs were returned by the sparql endpoint"
        logger.info(msg)
    total_end = time.time()
    total_elapsed = total_end - total_start
    logger.info("Total elapsed time: " + str(timedelta(seconds=total_elapsed)))


if __name__ == '__main__':
    main()