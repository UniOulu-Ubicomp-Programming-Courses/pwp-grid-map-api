"""
This module contains CLI commands for management. Available commands:
* init-db: initializes the database
* testgen: populates the database with random data for development purposes
"""

import copy
import click
import os.path
import yaml
from slugify import slugify
from flask import current_app, url_for
from flask.cli import with_appcontext
from gridmap import db
from gridmap.models import Map, Observer, Obstacle
from gridmap.resources import map, observer, obstacle

TEST_MAP = {
    "name": "Test Map 1",
    "slug": slugify("Test Map 1"),
    "width": 100,
    "height": 80,
}
OBSERVERS = [
    {
        "name": f"Test Observer {i}",
        "slug": slugify(f"Test Observer {i}"),
        "x": x,
        "y": y,
    }
    for i, (x, y) in enumerate([(1, 1), (40, 40), (80, 20), (10, 70)])
]
OBSTACLES = [(5, 5), (20, 20), (50, 50), (70, 70)]

class literal_unicode(str): pass

def literal_unicode_representer(dumper, data):
    return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')
yaml.add_representer(literal_unicode, literal_unicode_representer)


@click.command("init-db")
@with_appcontext
def init_db_command():
    """
    Initializes the database. If already initialized, nothing happens.
    """

    db.create_all()

@click.command("testgen")
@with_appcontext
def generate_test_data():
    """
    Creates random data that can be used for manual testing while developing.
    Creates a single map and places 3 observers and 3 obstacles in random
    positions on the map.
    """
    
    
    map = Map(**TEST_MAP)

    for data in OBSERVERS :
        observer = Observer(**data)
        map.observers.append(observer)

    for x, y in OBSTACLES:
        obstacle = Obstacle(
            x=x,
            y=y,
        )
        map.obstacles.append(obstacle)

    db.session.add(map)
    db.session.commit()


#https://www.semicolonworld.com/question/59482/any-yaml-libraries-in-python-that-support-dumping-of-long-strings-as-block-literals-or-folded-blocks

@click.command("update-schemas")
def update_schemas():

    with open("gridmap/doc/base.yml") as source:
        doc = yaml.safe_load(source)
    schemas = doc["components"]["schemas"] = {}
    for cls in [Map, Observer, Obstacle]:
        schemas[cls.__name__] = cls.json_schema()

    doc["info"]["description"] = literal_unicode(doc["info"]["description"])
    with open("gridmap/doc/base.yml", "w") as target:
        target.write("---\n")
        target.write(yaml.dump(doc, default_flow_style=False))

@click.command("update-docs")
@with_appcontext
def update_docs():
    DOC_ROOT = "./gridmap/doc/"
    GET_TEMPLATE = {
        "responses": {
            "200": {
                "content": {
                    "application/json": {},
                    "application/vnd.mason+json": {}
                }
            }
        }
    }
    POST_PUT_TEMPLATE = {
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {}
                }
            }
        }
    }
    POST_TEMPLATE = POST_PUT_TEMPLATE.copy()
    POST_TEMPLATE["responses"] = {
        "201": {
            "headers": {
                "Location": {
                    "description": "URI of the created resource",
                    "schema": {
                        "type": "string"
                    }
                }
            }
        }
    }
    DELETE_TEMPLATE = {
        "responses": {
            "204": {
                "description": "Successfully deleted"
            },
            "404": {
                "description": "Object not found"
            }
        }
    }

    resource_classes = [
        map.MapCollection, map.MapItem, map.MapObservers, map.MapObstacles,
        observer.ObserverItem,
        obstacle.ObstacleItem,
    ]

    client = current_app.test_client()

    def read_or_create(path, template={}):
        if os.path.exists(path):
            with open(path) as source:
                doc = yaml.safe_load(source)
        else:
            doc = copy.deepcopy(template)

        return doc

    def write_doc(path, content):
        with open(path, "w") as target:
            target.write("---\n")
            target.write(yaml.dump(doc, default_flow_style=False))

    for cls in resource_classes:
        endpoint = cls.__name__.lower()
        endpoint_path = os.path.join(DOC_ROOT, endpoint)
        os.makedirs(endpoint_path, exist_ok=True)
        if hasattr(cls, "get"):
            doc_path = os.path.join(endpoint_path, "get.yml")
            doc = read_or_create(doc_path, GET_TEMPLATE)
            uri = url_for(
                "api." + endpoint,
                map=Map(**TEST_MAP),
                observer=Observer(**OBSERVERS[0]),
                x=OBSTACLES[0][0],
                y=OBSTACLES[0][1],
            )
            doc["responses"]["200"]["content"]["application/json"]["example"] = client.get(
                uri, headers={"Accept": "application/json"}
            ).json
            doc["responses"]["200"]["content"]["application/vnd.mason+json"]["example"] = client.get(
                uri, headers={"Accept": "application/vnd.mason+json"}
            ).json
            write_doc(doc_path, doc)

        if hasattr(cls, "post"):
            doc_path = os.path.join(endpoint_path, "post.yml")
            doc = read_or_create(doc_path, POST_TEMPLATE)
            doc["requestBody"]["content"]["application/json"]["schema"]["$ref"] = (
                f"#/components/schemas/{cls.child_model.__name__}"
            )
            write_doc(doc_path, doc)

        if hasattr(cls, "put"):
            doc_path = os.path.join(endpoint_path, "put.yml")
            doc = read_or_create(doc_path, POST_PUT_TEMPLATE)
            doc["requestBody"]["content"]["application/json"]["schema"]["$ref"] = (
                f"#/components/schemas/{cls.model.__name__}"
            )
            write_doc(doc_path, doc)

        if hasattr(cls, "delete"):
            doc_path = os.path.join(endpoint_path, "delete.yml")
            doc = read_or_create(doc_path, DELETE_TEMPLATE)
            write_doc(doc_path, doc)




