import json

import structlog
import requests
from django.core import serializers
from ratelimit import limits, RateLimitException
from tastypie.authentication import ApiKeyAuthentication
from tastypie.resources import Resource
from django.core.cache import cache
from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from star_wars.api_resources.utils import APIResponse
from star_wars.models import People
from tastypie.throttle import CacheThrottle

from galactica.celery import app

logger = structlog.get_logger(__name__)
CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)


class PeopleResource(Resource):
    """
    Process API requests to fetch people related information.
    API endpoint: /api/v1/peoples/
    """
    class Meta:
        resource_name = 'peoples'
        authentication = ApiKeyAuthentication()
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        throttle = CacheThrottle(throttle_at=100, timeframe=60, expiration=30)

    def get_list(self, request, **kwargs):
        """
        This is the endpoint method for search people api
        """
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        self.log_throttled_access(request)
        name = request.GET.get('name', '')
        birth_year = request.GET.get('birth_year', '')
        cache_records = cache.get(name + "-" + birth_year)
        if cache_records:
            logger.info("fetched the records from cache")
            cached_response = {'results': cache_records}
            return APIResponse.ok(extend_dict=cached_response, local=True)
        # check in local storage if not found in cache
        local_records = self.fetch_records_from_local(name, birth_year)
        if len(local_records['results']) != 0:
            logger.info("fetched the records from local storage")
            self.save_records_to_cache(name, birth_year, local_records['results'])
            return APIResponse.ok(extend_dict=local_records, local=True)
        else:
            try:
                swapi_response = self.fetch_records_from_swapi_and_store(name, birth_year)
                logger.info("fetched the records from swapi endpoint")
                return APIResponse.ok(extend_dict=swapi_response)
            except RateLimitException:
                return APIResponse.service_unavailable("Max tries exceeded")

    def save_records_to_cache(self, name, birth_year, value):
        """
        This method will save a key-value pair to cache
        """
        logger.info('adding values to cache', params=(name, birth_year))
        cache.set(name + "-" + birth_year, value, timeout=CACHE_TTL)

    @limits(calls=10, period=60)
    def fetch_records_from_swapi_and_store(self, name, birth_year):
        """
        This method will try to fetch the records from the swapi end point and
        then call another method for saving/updating the record in local db and cache
        """
        url = f"https://swapi.dev/api/people/?search={name}"
        response = requests.get(url, verify=False).json()
        for people_swapi_record in response["results"]:
            self.save_records_to_local(people_swapi_record)
        # saving value to cache
        self.save_records_to_cache(name, birth_year, response["results"])
        return response

    def fetch_records_from_local(self, name, birth_year):
        """
        This method will try to fetch the records from the local persistent storage and
        return it if found or return an empty array
        """
        result = {'results': []}
        if not(name.strip() == '' and birth_year.strip() == ''):
            logger.info('Get people request with params', params=(name, birth_year))
            records = serializers.serialize('json', People.objects.filter(name__contains=name, birth_year__contains=birth_year))
            if records:
                response = [{"name": person["fields"]["name"],
                             "birth_year": person["fields"]["birth_year"],
                             "eye_color": person["fields"]["eye_color"],
                             "mass": str(person["fields"]["mass"]),
                             "gender": str(person["fields"]["gender"]),
                             "height": person["fields"]["height"],
                             "created": person["fields"]["created"]} for person in json.loads(records)]
                result['results'] = response
        return result

    def save_records_to_local(self, people_swapi_record):
        """
        This method will create people entry in db if it doesn't exists
        Or update if already exists
        """
        fetch_id = int(people_swapi_record['url'].split('/')[-2])
        name = people_swapi_record.get('name')
        birth_year = people_swapi_record.get('birth_year')
        height = -1 if people_swapi_record.get('height') == "unknown" else people_swapi_record.get('height').replace(',', '').replace('.', '')
        mass = -1 if people_swapi_record.get('mass') == "unknown" else people_swapi_record.get('mass').replace(',', '').replace('.', '')
        gender_swapi = people_swapi_record.get('gender')
        gender = People.GENDER_MALE if gender_swapi == 'male' else People.GENDER_FEMALE if gender_swapi == 'female' else People.GENDER_UNDISCLOSED
        eye_color = people_swapi_record.get('eye_color')
        edited = people_swapi_record.get('edited')

        record = People.objects.filter(id=fetch_id)

        if record.exists():
            record.update(
                    id=fetch_id,
                    name=name,
                    birth_year=birth_year,
                    height=height,
                    mass=mass,
                    gender=gender,
                    eye_color=eye_color,
                    edited=edited
            )
        else:
            people = People()
            people.id = fetch_id
            people.name = name
            people.birth_year = birth_year
            people.height = height
            people.mass = mass
            people.gender = gender
            people.eye_color = eye_color
            people.edited = edited
            people.save()


@app.task(name="sync_with_swapi_endpoint")
def sync_with_swapi_endpoint():
    """
    This method syncs swapi results with local storage
    """
    logger.info("syncing local storage with swapi endpoint")
    people = PeopleResource()
    people.fetch_records_from_swapi_and_store('', '')