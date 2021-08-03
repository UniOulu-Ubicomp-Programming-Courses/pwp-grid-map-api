"""
This module includes all database models used in the map inventory service.
SQLAlchemy is used to manage the models. Each model has utility methods to
serialize and deserialize between model instances and dictionaries. In
addition, each model class has a class method for retrieving a JSON schema
corresponding to the model.
"""

from flask import url_for
from app import db
from app.constants import MAP_PROFILE, OBSERVER_PROFILE
from app.utils import MapBuilder
from slugify import slugify


class Map(db.Model):
    """
    Model that represents a map. Maps have height and width, and can contain
    any number of observers and obstacles, assuming there are free tiles. Maps
    are indexed by slugs derived from names.
    
    Range validation for width and height is not done on the database level, it
    will be done in schema validation instead.
    
    Maps have four columns.
    * *id* (int) 
    * *name* (str) - map name, max 32 characters
    * *slug* (str) - slugified name
    * *width* (int) - map width (tiles)
    * *height* (int) - map height (tiles)
    
    Relationships.
    * *observers* - all observers on the map
    * *obstacles* - all obstacles on the map
    """
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    slug = db.Column(db.String(32), unique=True, nullable=False, index=True)
    width = db.Column(db.Integer, nullable=False)
    height= db.Column(db.Integer, nullable=False)
    
    observers = db.relationship(
        "Observer",
        back_populates="map",
        cascade="all, delete-orphan"
    )
    obstacles = db.relationship(
        "Obstacle",
        back_populates="map",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"{self.name} <{self.id}> ({self.width} x {self.height})"
        
    def serialize(self,
                  include_relations=False,
                  use_mason=False,
                  primary=False) -> dict:
        """
        Serializes a model instance into a Python dictionary. Includes all
        columns that are intended to be accessible through the API. If
        *include_relations* is set, will also include list of observers and
        obstacles on the map. 
        
        If *use_mason* is set, hypermedia controls will
        be included in the result. If *primary* is set to False, this object
        will be treated as an item in a listing and will only get a "self"
        control. If it's set to True, full controls for changing the map will
        be included.
        """
    
        if use_mason:
            body = MapBuilder()
            body.add_control("self", url_for("api.mapitem", map=self))
            if primary:
                body.add_control("collection", url_for("api.mapcollection"))
                body.add_control_edit_map(self, self.json_schema())
                body.add_control_delete_map(self)
                body.add_control("profile", MAP_PROFILE)
                body.add_control_create_observer(self, Observer.json_schema())
                body.add_control_create_obstacle(self, Obstacle.json_schema())
        else:
            body = {}
            
        body.update({
            "name": self.name,
            "slug": self.slug,
            "width": self.width,
            "height": self.height,
        })
        if include_relations:
            observers = []
            for observer in self.observers:
                observers.append(observer.serialize(use_mason=use_mason))
            obstacles = []            
            for obstacle in self.obstacles:
                obstacles.append(obstacle.serialize(use_mason=use_mason))
            body["observers"] = observers
            body["obstacles"] = obstacles
        if use_mason:
            pass
        return body
        
    def update_from_dict(self, object_dict):
        """
        Updates this model instance from a dictionary with matching keys. Note
        that slug will be updated from the "name" key using slugify - "slug"
        key will be ignored even if set.
        """
    
        self.name = object_dict["name"]
        self.slug = slugify(object_dict["name"])
        self.width = object_dict["width"]
        self.height = object_dict["height"]
        
    @classmethod
    def deserialize(cls, object_dict) -> object:
        """
        Creates a new Map model instance from a dictionary. The object returned
        by this method can be used to create a new database entry. Notably,
        *id* is not set by this method, and *slug* is generated from the name 
        included in the dictionary.
        """
        
        return cls(
            name=object_dict["name"],
            slug=slugify(object_dict["name"]),
            width=object_dict["width"],
            height=object_dict["height"]
        )

    @staticmethod
    def json_schema() -> dict:
        """
        Static method for getting the model's respective JSON schema. This
        method simply constructs the schema as a Python dictionary. 
        
        NOTE: This is only done for the sake of keeping things simple - in a
        real life solution schemas should be generated from the model
        declaration.
        """
        
        props = {}
        props["name"] = {
            "description": "Name for the map (unique)",
            "type": "string",
            "maxLength": 32
        }
        props["width"] = {
            "description": "Map width",
            "type": "integer",
            "minimum": 1
        }
        props["height"] = {
            "description": "Map height",
            "type": "integer",
            "minimum": 1
        }    
        return {
            "type": "object",
            "required": ["name", "width", "height"],
            "properties": props
        }
        

class Observer(db.Model):
    """
    Model that represents an observer on a map. Observers are indexed by slugs
    derived from names, and observer names are unique. Observers can have an
    optional limited range of vision. Observers will be deleted along with the
    map they are on.
    
    Validation for number ranges is not done on the database level. It will be
    done in schema validation. Validation against map dimensions is done in the
    view function.
    
    Observer columns:
    * *id* (int) 
    * *name* (str) - observer name, max 32 characters
    * *slug* (str) - slugified name
    * *vision* (float) - observer's vision range (optional)
    * *map_id* (int) - foreign key to map id 
    * *x (int) - observer's x coordinate on the map
    * *y (int) - observer's x coordinate on the map
    
    Relationships:
    * *map* - reference to the map
    """
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    slug = db.Column(db.String(32), unique=True, nullable=False, index=True)
    vision = db.Column(db.Float, nullable=True)
    map_id = db.Column(
        db.Integer,
        db.ForeignKey("map.id", ondelete="CASCADE"),
        nullable=False
    )
    x = db.Column(db.Integer, nullable=False)
    y = db.Column(db.Integer, nullable=False)
    
    map = db.relationship("Map", back_populates="observers")

    def __repr__(self) -> str:
        return f"{self.name} <{self.id}> @ ({self.x}, {self.y})"

    def serialize(self,
                  include_relations=False,
                  use_mason=False,
                  primary=False) -> dict:
        """
        Serializes a model instance into a Python dictionary. Includes all
        columns that are intended to be accessible through the API. If
        *include_relations* is set, will also include slug and name of the map
        this observer is placed in. If *use_mason* is set, hypermedia controls
        will be included in the result.
        """
        
        if use_mason:
            body = MapBuilder()
            body.add_control("self", url_for(
                "api.observeritem", 
                map=self.map,
                observer=self
            ))
            if primary:
                body.add_control("up", url_for("api.mapitem", map=self.map))
                body.add_control_edit_observer(self, self.json_schema())
                body.add_control_delete_observer(self)
                body.add_control("profile", OBSERVER_PROFILE)
        else:
            body = {}

        body.update({
            "name": self.name,
            "slug": self.slug,
            "vision": self.vision,
            "x": self.x,
            "y": self.y
        })
        if include_relations:
            body["map_name"] = self.map.name
            body["map_slug"] = self.map.slug
        return body
        
    def update_from_dict(self, object_dict):
        """
        Updates this model instance from a dictionary with matching keys. Note
        that slug will be updated from the "name" key using slugify - "slug"
        key will be ignored even if set.
        """

        self.name = object_dict["name"]
        self.slug = slugify(object_dict["name"])
        self.vision = object_dict.get("vision")
        self.x = object_dict["x"]
        self.y = object_dict["y"]
        
    @classmethod
    def deserialize(cls, object_dict) -> object:
        """
        Creates a new Observer model instance from a dictionary. The object
        returned by this method can be used to create a new database entry.
        Notably, *id* is not set by this method, and *slug* is generated from
        the name included in the dictionary. Likewise the map relationship is
        expected to be created from the view method.
        """
        
        return cls(
            name=object_dict["name"],
            slug=slugify(object_dict["name"]),
            vision=object_dict.get("vision"),
            x=object_dict["x"],
            y=object_dict["y"]
        )
        
    @staticmethod
    def json_schema() -> dict:
        """
        Static method for getting the model's respective JSON schema. This
        method simply constructs the schema as a Python dictionary. 
        
        NOTE: This is only done for the sake of keeping things simple - in a
        real life solution schemas should be generated from the model
        declaration.
        """
        
        props = {}
        props["name"] = {
            "description": "Name for referencing the observer (unique per map)",
            "type": "string",
            "maxLength": 32
        }
        props["vision"] = {
            "description": "Observer's vision range (infinite if omitted)",
            "type": "number",
            "minimum": 0
        }
        props["x"] = {
            "description": "Observer's x coordinate",
            "type": "integer",
            "minimum": 0
        }
        props["y"] = {
            "description": "Observer's y coordinate",
            "type": "integer",
            "minimum": 0
        }
        return {
            "type": "object",
            "required": ["name", "x", "y"],
            "properties": props
        }
        
        
class Obstacle(db.Model):
    """
    Model that represents an obstacle on a map. Obstacles are only defined by
    their position on the map. All obstacles are deleted along with the map.
       
    Validation for numbers is not done on the database level. They will be
    forced in schema validation instead. Validation against map dimensions is
    done in the view method.
       
    Observer columns:
    * *id* (int) 
    * *map_id* (int) - foreign key to map id 
    * *x (int) - observer's x coordinate on the map
    * *y (int) - observer's x coordinate on the map
    
    Relationships:
    * *map* - reference to the map
    """

    id = db.Column(db.Integer, primary_key=True)
    map_id = db.Column(
        db.Integer,
        db.ForeignKey("map.id",
        ondelete="CASCADE"),
        nullable=False
    )
    x = db.Column(db.Integer, nullable=False)
    y = db.Column(db.Integer, nullable=False)
    
    map = db.relationship("Map", back_populates="obstacles")

    def __repr__(self) -> str:
        return f"Obstacle <{self.id}> @ ({self.x}, {self.y})"
    
    def serialize(self,
                  include_relations=False,
                  use_mason=False,
                  primary=False) -> dict:
        """
        Serializes a model instance into a Python dictionary. Includes all
        columns that are intended to be accessible through the API. If
        *include_relations* is set, will also include slug and name of the map
        this obstacle is placed in.
        
        If *use_mason* is set, hypermedia controls will be included in the
        result. In the current implementation *primary* has no effect because
        obstacles do not have a GET method. The control to delete an obstacle
        is always included.
        """

        if use_mason:
            body = MapBuilder()
            body.add_control_delete_obstacle(self)
        else:
            body = {}
        body.update({
            "x": self.x,
            "y": self.y,
        })
        if include_relations:
            body["map_name"] = self.map.name
            body["map_slug"] = self.map.slug
            
        return body
    
    @classmethod
    def deserialize(cls, object_dict) -> object:
        """
        Creates a new Obstacle model instance from a dictionary. The object
        returned by this method can be used to create a new database entry.
        Notably, *id* is not set by this method. Likewise the map relationship
        is expected to be created from the view method.
        """
        
        return cls(
            x=object_dict["x"],
            y=object_dict["y"],
        )
    
    @staticmethod
    def json_schema() -> dict:
        """
        Static method for getting the model's respective JSON schema. This
        method simply constructs the schema as a Python dictionary. 
        
        NOTE: This is only done for the sake of keeping things simple - in a
        real life solution schemas should be generated from the model
        declaration.
        """
        
        props = {}
        props["x"] = {
            "description": "Obstacles's x coordinate (closest to origin)",
            "type": "integer",
            "minimum": 0
        }
        props["y"] = {
            "description": "Obstacles's y coordinate (closest to origin)",
            "type": "integer",
            "minimum": 0
        }
        return {
            "type": "object",
            "required": ["x", "y"],
            "properties": props
        }
