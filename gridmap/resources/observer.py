"""
This module contains the observer resource.
"""

import json
from jsonschema import validate, ValidationError
from flask import Response, request, url_for
from flask_restful import Resource
from flask_accept import accept
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest, Conflict, UnsupportedMediaType
from gridmap import cache, db
from gridmap.constants import JSON, MASON, OBSERVER_PROFILE, LINK_RELATIONS
from gridmap.models import Map, Observer, Obstacle
from gridmap.utils import MapBuilder

class ObserverItem(Resource):
    """
    This resource implements a single observer item and the methods for
    obtaining it (GET), modifying it (PUT), and deleting it (DELETE). The GET
    method is split into two, routed via the Accept header. This allows
    clients to fetch either pure data as JSON, or a full hypermedia document
    as Mason.
    
    Each view method uses the map converter to obtain a model instance for the
    map that contains the observer, and the observer slug to obtain an instance
    of the observer itself. Not Found (404) is raised from the converter if the
    slugs don't correspond to existing resources.
    """
    
    def _clean_cache(self, parent):
        """
        Deletes cached observer from the cache, and the map that contains it. 
        This method is called by the put and delete methods when observer 
        information is changed or an observer is deleted.
        : param object parent: the map that contains the observer
        """

        parent_path = url_for("api.mapitem", map=parent)
        cache.delete_many((
            f"json-view/{parent_path}",
            f"mason-view/{parent_path}",
            f"json-view/{request.path}",
            f"mason-view/{request.path}"
        ))
    
    @accept("application/json")
    @cache.cached(timeout=None, key_prefix="json-view/%s")
    def get(self, map, observer):
        """
        The GET method for data only JSON. Returns a dictionary with observer
        attributes.
        """
        
        body = observer.serialize(include_relations=True)
        return Response(json.dumps(body), 200, mimetype=JSON)
        
    @get.support("application/vnd.mason+json")
    @cache.cached(timeout=None, key_prefix="mason-view/%s")
    def get_mason(self, map, observer):
        """
        The GET method for Mason. Returns a dictionary with observer
        attributes. Also includes hypermedia controls for editing and deleting
        the observer, as well as navigational control to return to the map
        resource that contains the observer.
        """
        
        body = observer.serialize(use_mason=True, primary=True)
        body.add_namespace("pwp-map", LINK_RELATIONS)
        return Response(json.dumps(body), 200, mimetype=JSON)
        
    def put(self, map, observer):
        """
        Updates the observer from the request body sent by the client. On
        success responds with status code 204.
        
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

        observer.update_from_dict(request.json)
        if 0 <= observer.x < map.width and 0 <= observer.y < map.height:
            pass
        else:
            raise BadRequest(description="Observer is outside map")
        try:
            db.session.add(observer)
            db.session.commit()
        except IntegrityError:
            raise Conflict(
                description="An observer named '{name}' already exists".format(
                    **request.json
            ))
        self._clean_cache(map)
        return Response(status=204)

    def delete(self, map, observer):
        """
        Deletes the observer.
        """
        
        db.session.delete(observer)
        db.session.commit()
        self._clean_cache(map)
        return Response(status=204)

