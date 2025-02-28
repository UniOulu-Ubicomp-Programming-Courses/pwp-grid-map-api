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

    with open("doc/base.yml") as source:
        doc = yaml.safe_load(source)
    schemas = doc["components"]["schemas"] = {}
    for cls in [Map, Observer, Obstacle]:
        schemas[cls.__name__] = cls.json_schema()

    doc["info"]["description"] = literal_unicode(doc["info"]["description"])
    with open("doc/base.yml", "w") as target:
        target.write(yaml.dump(doc, default_flow_style=False))

@click.command("get-docs")
@with_appcontext
def update_get_docs():
    DOC_ROOT = "./doc/"
    DOC_TEMPLATE = {
        "responses": {
            "200": {
                "content": {}
            }
        }
    }

    resource_classes = [
        map.MapCollection, map.MapItem,
        observer.ObserverItem
    ]

    client = current_app.test_client()

    for cls in resource_classes:
        endpoint = cls.__name__.lower()
        doc_path = os.path.join(DOC_ROOT, endpoint, "get.yml")
        os.makedirs(os.path.dirname(doc_path), exist_ok=True)
        if os.path.exists(doc_path):
            with open(doc_path) as source:
                doc = yaml.safe_load(source)
        else:
            doc = copy.deepcopy(DOC_TEMPLATE)

        uri = url_for(
            "api." + endpoint,
            map=Map(**TEST_MAP),
            observer=Observer(**OBSERVERS[0]),
            x=OBSTACLES[0][0],
            y=OBSTACLES[0][1],
        )
        doc["responses"]["200"]["content"]["application/json"] = client.get(
            uri, headers={"Accept": "application/json"}
        ).json
        doc["responses"]["200"]["content"]["application/vnd.mason+json"] = client.get(
            uri, headers={"Accept": "application/vnd.mason+json"}
        ).json
        with open(doc_path, "w") as target:
            target.write(yaml.dump(doc, default_flow_style=False))








