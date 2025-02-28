"""
This module defines a Flask Blueprint for the API. It also contains resource
routing. The converters used in routes are registered in the create_app
function found in __init__.py
"""

from flask import Blueprint
from flask_restful import Api
from gridmap.resources import map, observer, obstacle

api_bp = Blueprint("api", __name__, url_prefix="/api")
api = Api(api_bp)

api.add_resource(map.MapCollection, "/maps/")
api.add_resource(map.MapItem, "/maps/<map:map>/")
api.add_resource(map.MapObservers, "/maps/<map:map>/observers/")
api.add_resource(map.MapObstacles, "/maps/<map:map>/obstacles/")
api.add_resource(
    observer.ObserverItem,
    "/maps/<map:map>/observers/<observer:observer>/"
)
api.add_resource(
    obstacle.ObstacleItem,
    "/maps/<map:map>/obstacles/<int:x>/<int:y>/"
)
