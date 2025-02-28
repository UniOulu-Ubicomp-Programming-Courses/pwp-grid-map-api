"""
This module defines custom converters for routing. These converters streamline
resource code by performing the process of getting the model instance from the
database before the view method is called. The converter converts a resource's
slug to the corresponding model instance, which is then placed into the view
method arguments. This eliminates the need to get all of the model instances
referenced in the URI and doing a 404 check for each one, avoiding a whole
lot of boilerplate code in the view methods.

The same happens in reverse: when costructing a URI for a resource, a model
instance is passed to *url_for* instead of the model slug, and the converter
will take care of placing a convertible value into the URI.
"""

from werkzeug.exceptions import NotFound
from werkzeug.routing import BaseConverter
from gridmap.models import Map, Observer, Obstacle

class MapConverter(BaseConverter):
    """
    A converter for the Map model. Uses map slug as the resource handle.
    """
    
    def to_python(self, map_slug) -> object: 
        """
        Converts a map slug into the corresponding map model instance.
        """
        
        map = Map.query.filter_by(slug=map_slug).first()
        if map is None:
            raise NotFound
        return map
        
    def to_url(self, map) -> str:
        """
        Converts a map model instance to its corresponding slug for use in URI.
        """
        
        return map.slug

        
class ObserverConverter(BaseConverter):
    """
    A converter for the Map model. Uses map slug as the resource handle.
    """
    
    def to_python(self, obs_slug):
        observer = Observer.query.filter_by(slug=obs_slug).first()
        if observer is None:
            raise NotFound
        return observer
        
    def to_url(self, observer):
        return observer.slug
    
