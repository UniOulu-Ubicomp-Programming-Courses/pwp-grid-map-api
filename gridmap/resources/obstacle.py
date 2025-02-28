"""
This module contains the obstacle resource
"""

import json
from jsonschema import validate, ValidationError
from flask import Response, request, url_for
from flask_restful import Resource
from flask_accept import accept
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest, Conflict, UnsupportedMediaType
from gridmap import cache, db
from gridmap.constants import JSON, MASON, MAP_PROFILE
from gridmap.models import Obstacle

class ObstacleItem(Resource):
    """
    This class implements the obstacle resource. It supports only one method, 
    DELETE, which will remove an obstacle from a map position.

    The view method uses the map converter to obtain a model instance for the
    requested map slug. Not Found (404) is raised from the converter if the
    slug doesn't correspond to an existing map.
    """
    
    def _clean_cache(self, parent):
        """
        Deletes cached map from the cache when an obstacle in it is removed. 
        This method is called by the delete method.
        : param object parent: the map object that was added to
        """

        parent_path = url_for("api.mapitem", map=parent)
        cache.delete_many((
            f"json-view/{parent_path}",
            f"mason-view/{parent_path}",
        ))

    def delete(self, map, x, y):
        """
        Removes on obstacle from the given map at given coordinates.
        """
        
        Obstacle.query.filter_by(map_id=map.id, x=x, y=y).delete()
        self._clean_cache(map)
        return Response(status=204)
