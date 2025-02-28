"""
This module contains resources related to map. 
"""

import json
from jsonschema import validate, ValidationError
from flask import Response, request, url_for
from flask_restful import Resource
from flask_accept import accept
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest, Conflict, UnsupportedMediaType
from gridmap import cache, db
from gridmap.constants import JSON, MASON, MAP_PROFILE, LINK_RELATIONS
from gridmap.models import Map, Observer, Obstacle
from gridmap.utils import MapBuilder


class MapCollection(Resource):
    """
    This resource implements the map collection and its related methods that
    can be used to fetch the map collection (GET) and create new maps (POST).
    The GET method is split into two view methods routed via the Accept header.
    This allows clients to fetch either pure data as JSON, or full hypermedia
    document using Mason.
    """
    
    def _clean_cache(self):
        """
        Deletes cached map collection from the cache. This method is called by
        the post method when a new map is added.
        """
        
        cache.delete_many((
            f"json-view/{request.path}",
            f"mason-view/{request.path}"
        ))
    
    @accept("application/json")
    @cache.cached(timeout=None, key_prefix="json-view/%s")
    def get(self):
        """
        The GET method for data only JSON. Returns a dictionary with a single
        key, "maps", which will contain an array of all the maps in serialized
        format. Maps serialized by this view method will not include map
        contents.
        """
        
        items = []
        for db_map in Map.query.all():
            items.append(db_map.serialize())
        body = {
            "maps": items
        }
        return Response(json.dumps(body), 200, mimetype=JSON)
        
    @get.support("application/vnd.mason+json")
    @cache.cached(timeout=None, key_prefix="mason-view/%s")
    def get_mason(self):
        """
        The GET method for Mason. The data part of the dictionary is a single
        key, "maps", which will contain an array of all the maps in serialized
        format. A "self" relation is included for each map for easy access to
        the individual map resource.
        
        The response will also include hypermedia controls for creating new
        maps, and accessing the map profile.
        """

        items = []
        for db_map in Map.query.all():
            items.append(db_map.serialize(use_mason=True))
        body = MapBuilder(
            maps=items
        )
        body.add_namespace("pwp-map", LINK_RELATIONS)
        body.add_control("self", url_for("api.mapcollection"))
        body.add_control_create_map(schema=Map.json_schema())
        body.add_control("profile", MAP_PROFILE)
        return Response(json.dumps(body), 200, mimetype=MASON)
        
    def post(self):
        """
        Creates a new map from the request body sent by the client. On success
        responds with status code 201 and Location header which contains the
        URI of the newly created map.
        
        The following exceptions are possible:
        * Unsupported Media Type (415) - when the request body is not JSON
        * Bad Request (400) - if validation against schema fails
        * Conflict (409) - if an integrity error occurs while saving to DB
        """
    
        if not request.json:
            raise UnsupportedMediaType

        try:
            validate(request.json, Map.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))
        
        map = Map.deserialize(request.json)
        try:
            db.session.add(map)
            db.session.commit()
        except IntegrityError:
            raise Conflict(
                description="A map named '{name}' already exists".format(
                    **request.json
            ))
        self._clean_cache()
        return Response(status=201, headers={
            "Location": url_for("api.mapitem", map=map)
        })


class MapItem(Resource):
    """
    This resource implements a single map item and the methods for obtaining it
    (GET), modifying it (PUT), and deleting it (DELETE). The GET method is
    split into two, routed via the Accept header. This allows clients to fetch
    either pure data as JSON, or a full hypermedia document as Mason.
    
    Each view method uses the map converter to obtain a model instance for the
    requested map slug. Not Found (404) is raised from the converter if the
    slug doesn't correspond to an existing map.
    
    Map item doesn't have a POST method for adding content to it because it
    needs to differentiate between two different types of resources. These
    operations are handled by the auxiliary resources MapObservers and
    MapObstacles.
    """
    
    def _clean_cache(self):
        """
        Deletes cached map from the cache, as well as the map collection. This
        method is called by the put and delete methods when map attributes are
        changed or a map is deleted.
        """
        
        collection_path = url_for("api.mapcollection")
        cache.delete_many((
            f"json-view/{collection_path}",
            f"mason-view/{collection_path}",
            f"json-view/{request.path}",
            f"mason-view/{request.path}"
        ))

    @accept("application/json")
    @cache.cached(timeout=None, key_prefix="json-view/%s")
    def get(self, map):
        """
        The GET method for data only JSON. Returns a dictionary with map
        attributes, and two keys for arrays: "observers" and "obstacles".
        These contain all attributes of each observer/obstacle which allows
        clients to process everything on the map.
        """
        
        body = map.serialize(include_relations=True)
        return Response(json.dumps(body), 200, mimetype=JSON)
        
    @get.support("application/vnd.mason+json")
    @cache.cached(timeout=None, key_prefix="mason-view/%s")
    def get_mason(self, map):
        """
        The GET method for Mason. Returns a dictionary with map attributes, and
        two keys for arrays: "observers" and "obstacles". The main body
        includes hypermedia controls for going back to the map collection, 
        editing map attributes, and deleting the map. It also includes controls
        for placing observers and obstacles on the map.
        
        Items in the observer array include a link to the observer resource.
        Items in the obstacle array only include a link to delete the obstacle.
        """

        body = map.serialize(
            include_relations=True,
            use_mason=True,
            primary=True
        )
        body.add_namespace("pwp-map", LINK_RELATIONS)
        return Response(json.dumps(body), 200, mimetype=MASON)
        
    def put(self, map):
        """
        Updates the map from the request body sent by the client. On success
        responds with status code 204.
        
        The following exceptions are possible:
        * Unsupported Media Type (415) - when the request body is not JSON
        * Bad Request (400) - if validation against schema fails
        * Conflict (409) - if an integrity error occurs while saving to DB
        """
    
        if not request.json:
            raise UnsupportedMediaType

        try:
            validate(request.json, Map.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        map.update_from_dict(request.json)
        try:
            db.session.add(map)
            db.session.commit()
        except IntegrityError:
            raise Conflict(
                description="A map named '{name}' already exists".format(
                    **request.json
            ))
        self._clean_cache()
        return Response(status=204)
        
    def delete(self, map):
        """
        Deletes the map. This includes all observers and obstacles on the map.
        Idempotent.
        """
        
        db.session.delete(map)
        db.session.commit()
        self._clean_cache()
        return Response(status=204)
        
        
class MapObservers(Resource):
    """
    This resource implements the POST method for adding observers to a map.
    """
    
    def _clean_cache(self, parent):
        """
        Deletes cached map from the cache. This method is called by the post
        method when a new observer is added. 
        : param object parent: the map object that was added to
        """

        parent_path = url_for("api.mapitem", map=parent)
        cache.delete_many((
            f"json-view/{parent_path}",
            f"mason-view/{parent_path}",
        ))

    def post(self, map):
        """
        Places a new observer on the map using data from the request body sent
        by the client. On success responds with status code 201 and Location
        header which contains the URI of the newly created observer.
        
        The following exceptions are possible:
        * Unsupported Media Type (415) - when the request body is not JSON
        * Bad Request (400) - if validation against schema fails
        * Conflict (409) - if an integrity error occurs while saving to DB
        """
    
        if not request.json:
            raise UnsupportedMediaType

        try:
            validate(request.json, Observer.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))
        
        observer = Observer.deserialize(request.json)
        if 0 <= observer.x < map.width and 0 <= observer.y < map.height:
            map.observers.append(observer)
        else:
            raise BadRequest(description="Observer is outside map")
        
        try:
            db.session.add(map)
            db.session.commit()
        except IntegrityError:
            raise Conflict(
                description="An observer named '{name}' already exists".format(
                    **request.json
            ))
        self._clean_cache(map)
        return Response(status=201, headers={
            "Location": url_for("api.observeritem", map=map, observer=observer),
        })


class MapObstacles(Resource):
    """
    This resource implements the POST method for adding observers to a map.
    """

    def _clean_cache(self, parent):
        """
        Deletes cached map from the cache. This method is called by the post
        method when a new obstacle is added. 
        : param object parent: the map object that was added to
        """

        parent_path = url_for("api.mapitem", map=parent)
        cache.delete_many((
            f"json-view/{parent_path}",
            f"mason-view/{parent_path}",
        ))

    def post(self, map):
        """
        Places a new obstacle on the map using data from the request body sent
        by the client. On success responds with status code 201 and Location
        header which contains the URI of the newly created obstacle. It should
        be noted however that the obstacle resource does not implement a GET
        method, and this URI can only be used to delete the obstacle.
        
        The following exceptions are possible:
        * Unsupported Media Type (415) - when the request body is not JSON
        * Bad Request (400) - if validation against schema fails
        * Conflict (409) - if an integrity error occurs while saving to DB
        """

        if not request.json:
            raise UnsupportedMediaType

        try:
            validate(request.json, Obstacle.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))
        
        obstacle = Obstacle.deserialize(request.json)
        if 0 <= obstacle.x < map.width and 0 <= obstacle.y < map.height:
            map.obstacles.append(obstacle)
        else:
            raise BadRequest(description="Obstacle is outside map")
        
        db.session.add(map)
        db.session.commit()
        self._clean_cache(map)
        return Response(status=201, headers={
            "Location": url_for(
                "api.obstacleitem",
                map=map,
                x=obstacle.x,
                y=obstacle.y
            ),
        })
