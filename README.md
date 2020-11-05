- [Django](https://www.djangoproject.com/): a web-framework (ver 3).
- [TastyPie](https://django-tastypie.readthedocs.io/en/latest/): a lightweight library to build out a RESTful API service.

There is 1 API endpoint for which the implementation has been provided:
```curl
curl --request GET \
  --url http://localhost:8000/api/v1/peoples/ \
  --header 'authorization: apikey api_client_1:204db7bcfafb2deb7506b89eb3b9b715b09905c8'
```

The `authorization` header makes use of an API Key based authentication mechanism, that is supported by TastyPie ([link](https://django-tastypie.readthedocs.io/en/latest/authentication.html#apikeyauthentication)).

Note : 
1. A Django 3 project
2. Local data persistence in a sqlite3 db (included within the repo) - `db.sqlite3`

All the current logic is contained within the `/star_wars/api_resources/peopleresource` module. When a request is made to the `/api/v1/peoples/` endpoint, I am simply forwarding it to the SWAPI endpoint, fetching the data and sending it back as-is.

I've added below functionalities to it :

### 1—Search capability
capability to search on this API endpoint. User should be able to make a request like so:

```curl
curl --request GET \
  --url http://localhost:8000/api/v1/peoples/?name=c-3p0&birth_year=112BBY \
  --header 'authorization: apikey api_client_1:204db7bcfafb2deb7506b89eb3b9b715b09905c8'
```

Support for search is _only_ required on the `name` and `birth_year` attributes. To make the search behaviour performant, I would first search in the local persistence storage whether any matching `People` records are found. If not, only then the request should be routed to the SWAPI endpoint. When data is fetched from the SWAPI endpoint, store it in the local persistence storage.
For objects that are fetched from the local storage, add a boolean attribute `local` to the response payload and set it to `true`. If not fetched locally, set it to `false`.

To ensure that the locally stored results do not go out-of-sync with the SWAPI dataset, perform a periodic check to compare the locally stored data with that of the SWAPI system. Update the local dataset for any changes that are detected. 

### 2—Improved Performance
Now that I've got a nice simple search functionality, I would like to improve the performance further.  
Add a way by which it caches the search results and even before we consider hitting the SWAPI endpoint or the local storage, I check the cache. If there's a match, I fetch the results from the cache.

Also, I have added implementation for invalidating the cache based on a logic that ensures correctness and freshness of data.

### 3—Scalability
There are 2 things that I would like to ensure so that neither our system nor SWAPI's system gets overwhelmed.  
1. Ensure that our API endpoint employs a _throttling_ mechanism to avoid a barrage of requests hitting it. For a given API username, make sure that more than 100 requests cannot be made in a minute. If anyone breaches the threshold, then they should not be able to make any requests for the next 30 seconds.
2. At the other end, I would like to ensure that our application does _not_ make more than 10 requests in a minute under any circumstance. Devise an approach that ensures that outbound requests never exceed more than rate-limit of 10/min.

### 4–Testing
Setup a test framework that can validate the constraints related to the _throttling_ and _rate-limit_ condition above.

---

## Running the application

1. Install required library specified in `requirements.txt` with pip install
2. Run `python manage.py runserver` to start the django server.
3. Install redis server. version > 3.x
4. start the redis server
5. Start the job with `celery -A galactica beat -l INFO`
6. Run unit tests with `python manage.py test`

## Added below libraries
1. django-redis - for caching
2. celery - for scheduling the sync job
3. ratelimit - impose limit on the outbound requests