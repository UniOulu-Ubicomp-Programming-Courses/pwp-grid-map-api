"""
This module contains CLI commands for management. Available commands:
* init-db: initializes the database
* testgen: populates the database with random data for development purposes
"""

import click
from slugify import slugify
from flask.cli import with_appcontext
from app import db
from app.models import Map, Observer, Obstacle

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
    
    import random
    
    width = 100
    height = 80
    tiles = [(x, y) for x in range(width) for y in range(height)]
    
    map = Map(
        name="Test Map 1",
        slug=slugify("Test Map 1"),
        width=width,
        height=height,
    )
    for i in range(1, 4):
        x, y = random.choice(tiles)
        observer = Observer(
            name=f"Test Observer {i}",
            slug=slugify(f"Test Observer {i}"),
            x=x,
            y=y,
        )
        map.observers.append(observer)
        tiles.remove((x, y))

    for i in range(1, 4):
        x, y = random.choice(tiles)
        obstacle = Obstacle(
            x=x,
            y=y,
        )
        map.obstacles.append(obstacle)
        tiles.remove((x, y))
    
    db.session.add(map)
    db.session.commit()
