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
    { ?s ontology:alive date^^xsd:date}
WHERE
    { ?s ontology:url <URL> }
```


Installation
---------------

```sh
pip install -r requirements.txt
```

Running the tests

```sh
$nosetests
```

Usage
---------------


```
python alive.py
```

TODO
----------------



[License GPL v3](LICENSE)
-------------------