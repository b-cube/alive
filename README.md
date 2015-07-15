![Project Status](http://img.shields.io/badge/status-alpha-red.svg)


**Alive!**
===================

Alive is a simple url verifier tool that updates triples based on url availability.

Overview
-------------------

The BCube triple store contains triples describing datasets and web services, this tool updates the status of these urls.
If the URL is alive for subject ?s then this tool will send an INSERT request to the triple store as follows:

```sql
INSERT
{
    ?subject prov:atTime \"$TIME\"^^xsd:date .
    ?subject http:statusCodeValue \"$HTTP_RESPONSE\"^^xsd:integer .
}
WHERE
{
    ?subject vcard:hasURL \"$URL\" .
}
```

This way we can create semantic queries like

```sql
SELECT  *
WHERE {
        ?subject vcard:hasURL ?base_url .
        ?subject http:statusCodeValue ?code .
        ?subject prov:atTime ?lastTimeChecked .
        FILTER regex(?base_url, "NASA", "i")
        FILTER (?code = 200)
}
```

which returns all the URLs that contain the word NASA and returned with an HTTP 200 OK response.


Installation
---------------

```sh
pip install -r requirements.txt
```

Using a virtual environment is highly recommended.

Running the tests

```sh
$PATH/TO/ALIVE/nosetests
```

Usage
---------------


```sh
python $PATH/TO/alive.py -s [http://SPARQL-ENDPOINT] -w [thread-number] -t [timeout for a URL] -v [verbose]
```

example:

```sh
python app/alive -s http://dummy.com/sparql -w 8 -t 2
```

this will query which URLs are in the http://dummy.com/sparql endpoint and will use up to 8 workers to request 
HTTP responses on the URLs. Each request will have a max timeout of 2 seconds.

* NOTE: The timeout parameter can affect how many HTTP 200 responses we get, if we set it too low we'll get a lot of 500s due
remote server speeds and/or a poor local machine performance. 2 seconds worked fine in a 2 core laptop with low bandwidth.



TODO
----------------
* Write tests for the sparql queries
* Create a profiler script
* Dockerize the app



[License GPL v3](LICENSE)
-------------------