import os
from flask import Flask
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
cache = Cache()

# Based on http://flask.pocoo.org/docs/1.0/tutorial/factory/#the-application-factory
# Modified to use Flask SQLAlchemy
def create_app(test_config=None):
    """
    Creates the Flask app. Configuration can be pulled from three places: 
    - dictionary as function argument, for tests
    - a configuration file "config.py" from the local instance folder root
    - the default development configuration hardcoded into this function
    
    Initiatializiation for the database and cache are done within this
    function. Likewise all CLI commands, converters, and blueprints are
    registered here before the Flask app object is returned.
    """

    app = Flask(__name__, instance_relative_config=True)
    
    # Default configuration
    app.config.from_mapping(
        SERVER_NAME="localhost",
        SECRET_KEY="dev",
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "development.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        CACHE_TYPE="SimpleCache",

    )
    
    # Configuration overrides from config file
    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)
        
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    db.init_app(app)
    cache.init_app(app)

    # Register CLI commands, converters, and blueprint
    # Imports are placed here to avoid circular import issues
    from . import api
    from . import management
    from . import converters
    app.cli.add_command(management.init_db_command)
    app.cli.add_command(management.generate_test_data)
    app.cli.add_command(management.update_schemas)
    app.cli.add_command(management.update_get_docs)
    app.url_map.converters["map"] = converters.MapConverter
    app.url_map.converters["observer"] = converters.ObserverConverter
    app.register_blueprint(api.api_bp)
    
    return app
