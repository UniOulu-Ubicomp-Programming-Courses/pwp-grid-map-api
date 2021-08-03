"""
This module includes utility classes and functions for API testing. 
"""

import json
import os
import pytest
import random
import tempfile
from jsonschema import validate
from sqlalchemy.engine import Engine
from sqlalchemy import event
from app import create_app, db
from app.models import Map, Observer, Obstacle


MAP_INVALID_VALUES = [
        ("width", "a"),
        ("height", "b"),
        ("width", -10),
        ("height", -10),
]

OBS_INVALID_VALUES = [
        ("x", "a"),
        ("y", "b"),
        ("x", -10),
        ("y", -10),
        ("x", 60),
        ("y", 60)
]


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    This function sets foreign key support on for SQLite. This is needed for
    testing because it's off by default, and our testing uses SQLite.
    """

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
    
    
class JsonApiPostTestBase(object):
    """
    This is a base class for implementing HTTP POST tests. It should be
    inherited into test classes for resources that support POST. It adds basic
    tests for valid requests, as well as various common invalid requests.
    The following member attributes can be used to configure test behavior:
    
    * *RESOURCE_URL* (str) - URI of the resource itself
    * *ITEM_URL* (str) - expected URI for the item created from valid_json
    * *REQUIRED_FIELDS* (list) - list of fields that are required for POST
    * *INVALID_VALUES* (list) - list of tuples (field, value) with invalid values
    * *TEST_UNIQUE* (bool) - are items expected to be unique
    * *VERIFY_ITEM* (bool) - verify that the item exists after it's created     
    """

    RESOURCE_URL = ""
    ITEM_URL = ""
    REQUIRED_FIELDS = []
    INVALID_VALUES = []
    TEST_UNIQUE = False
    VERIFY_ITEM = False
    
    def valid_item_json(self, **params):
        """
        A stub that needs to be overriden with a method that returns a
        dictionary that will be valid for creating a new item via POST.
        """
    
        raise NotImplementedError
    
    def test_post_valid_request(self, client):
        """
        Tests a POST method with a valid request body. Verifies the response
        status code, and that the Location header matches the URI set for
        *ITEM_URL*. If *VERIFY_ITEM* is enabled, will also verify that the
        item exists, and matches the valid data that was sent.
        """
        
        valid = self.valid_item_json()
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201
        assert resp.headers.get("Location", "").endswith(self.ITEM_URL)
        if self.VERIFY_ITEM:
            resp = client.get(
                resp.headers["Location"],
                headers={"Accept": "application/json"}
            )
            assert resp.status_code == 200
            body = json.loads(resp.data)
            for key, value in valid.items():
                assert body.get(key) == value
    
    def test_post_wrong_mediatype(self, client):
        """
        Tests a POST method with the wrong media type. Asserts that the
        response status code is 415.
        """
        
        valid = self.valid_item_json()
        resp = client.post(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415
        
    def test_post_missing_field(self, client):
        """
        Tests a POST method with a request body that is missing a required
        field. Rotates through all of the required fields and tests an
        otherwise valid request body with each of them missing in turn.
        """
        
        valid = self.valid_item_json()
        for field in self.REQUIRED_FIELDS:
            invalid = valid.copy()
            del invalid[field]
            resp = client.post(self.RESOURCE_URL, json=invalid)
            assert resp.status_code == 400
    
    def test_post_invalid_values(self, client):
        """
        Tests a POST method with a request body that contains invalid values
        for fields. Rotates through the invalid field-value pairs in
        *INVALID_VALUES* and updates and otherwise valid request body with each
        of the invalid pairs in turn.
        """
        
        valid = self.valid_item_json()
        for field, value in self.INVALID_VALUES:
            invalid = valid.copy()
            invalid[field] = value
            resp = client.post(self.RESOURCE_URL, json=invalid)
            assert resp.status_code == 400
    
    def test_post_duplicate(self, client):
        """
        Tests a POST method by sending the same method twice. if *TEST_UNIQUE*
        is True, an error with status code 409 is expected for the second
        request. Otherwise a normal response of 201 is expected for the second
        request.
        """
    
        valid = self.valid_item_json()
        resp = client.post(self.RESOURCE_URL, json=valid)
        resp = client.post(self.RESOURCE_URL, json=valid)
        if self.TEST_UNIQUE:
            assert resp.status_code == 409
        else:
            assert resp.status_code == 201


class JsonApiPutTestBase(object):
    """
    This is a base class for implementing HTTP PUT tests. It should be
    inherited into test classes for resources that support PUT. It adds basic
    tests for valid requests, as well as various common invalid requests.
    The following member attributes can be used to configure test behavior:
    
    * *RESOURCE_URL* (str) - URI of the resource itself
    * *ITEM_URL* (str) - expected URI for the item created from valid_json
    * *REQUIRED_FIELDS* (list) - list of fields that are required for POST
    * *INVALID_VALUES* (list) - list of tuples (field, value) with invalid values
    * *TEST_UNIQUE* (bool) - are items expected to be unique
    * *VERIFY_ITEM* (bool) - verify that the item exists after it's created     
    """

    RESOURCE_URL = ""
    RESOURCE_2_URL = ""
    RELOCATED_URL = ""
    REQUIRED_FIELDS = []
    INVALID_VALUES = []
    TEST_UNIQUE = False
    VERIFY_ITEM = False
    
    def valid_json(self, **params):
        """
        A stub that needs to be overriden with a method that returns a
        dictionary that will be valid for creating a new item via PUT.
        """
        raise NotImplementedError
    
    def test_put_valid_request(self, client):
        """
        Tests a PUT method with a valid request body. Verifies the response
        status code. If *VERIFY_ITEM* is enabled, will also verify that the
        new item can be found from *RELOCATED_URL* (in case the PUT operation
        changed the URI), and that its new state matches the data that was
        sent.
        """

        valid = self.valid_json()
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 204
        if self.VERIFY_ITEM:
            resp = client.get(
                self.RELOCATED_URL,
                headers={"Accept": "application/json"}
            )
            assert resp.status_code == 200
            body = json.loads(resp.data)
            for key, value in valid.items():
                assert body.get(key) == value
    
    def test_put_wrong_mediatype(self, client):
        """
        Tests a PUT method with the wrong media type. Asserts that the
        response status code is 415.
        """

        valid = self.valid_json()
        resp = client.put(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415
        
    def test_put_missing_field(self, client):
        """
        Tests a PUT method with a request body that is missing a required
        field. Rotates through all of the required fields and tests an
        otherwise valid request body with each of them missing in turn.
        """

        valid = self.valid_json()
        for field in self.REQUIRED_FIELDS:
            invalid = valid.copy()
            del invalid[field]
            resp = client.put(self.RESOURCE_URL, json=invalid)
            assert resp.status_code == 400
    
    def test_put_invalid_values(self, client):
        """
        Tests a POST method with a request body that contains invalid values
        for fields. Rotates through the invalid field-value pairs in
        *INVALID_VALUES* and updates and otherwise valid request body with each
        of the invalid pairs in turn.
        """

        valid = self.valid_json()
        for field, value in self.INVALID_VALUES:
            invalid = valid.copy()
            invalid[field] = value
            resp = client.put(self.RESOURCE_URL, json=invalid)
            assert resp.status_code == 400

    def test_put_duplicate(self, client):
        """
        Tests sending a PUT request to a different resource so that its new URI
        would match that of an existing resource. This test does nothing if 
        *TEST_UNIQUE* is set to False (for resources that do not have unique
        URIs directly based on attributes).        
        """

        if self.TEST_UNIQUE:
            valid = self.valid_json()
            resp = client.put(self.RESOURCE_URL, json=valid)
            resp = client.put(self.RESOURCE_2_URL, json=valid)
            assert resp.status_code == 409


class JsonApiDeleteTestBase(object):
    """
    This is a base class for implementing HTTP DELETE tests. It should be
    inherited into test classes for resources that support DELETE. It adds basic
    test for valid request.
    
    * *RESOURCE_URL* (str) - URI of the resource itself
    * *CONFIRM_DELETE* (bool) - Should the deletion be confirmed
    """

    RESOURCE_URL = ""
    CONFIRM_DELETE = False
    
    def test_delete(self, client):
        """
        Tests a DELETE method to *RESOURCE_URL*. If *CONFIRM_DELETE* is set to
        True, will also try to GET the same URI afterwards and confirm it now
        returns 404.
        """
        
        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 204
        if self.CONFIRM_DELETE:
            resp = client.get(self.RESOURCE_URL)
            assert resp.status_code == 404


class MasonApiTestBase(object):
    """
    This is a base class for implementing test classes for resources that
    support Mason as one of their media types. Adds utility methods for testing
    the different control types. These test utilities will take a control
    object from a response body, and try to make a valid request using the
    control's attributes.
    
    * *CONFIRM_DELETE* (bool) - Should the deletion be confirmed    
    """
    
    CONFIRM_DELETE = False
    
    def valid_json(self, **params):
        """
        A stub that needs to be overriden with a method that returns a
        dictionary that will be valid for creating/editing a resource of the
        type that is currently being tested.
        """        
    
        raise NotImplementedError

    def valid_item_json(self, **params):
        """
        A stub that needs to be overriden with a method that returns a
        dictionary that will be valid for adding new items to the collection
        that is currently being tested.
        """        

        raise NotImplementedError
    
    def _check_control_get_method(self, ctrl, client, obj):
        """
        Tests a control for a GET method by sending a new GET request to the
        URI in the control's "href" attribute using Mason as the accepted
        media type. Passes if response code 200 is received.
        """
    
        href = obj["@controls"][ctrl]["href"]
        resp = client.get(href, headers={"Accept": "application/vnd.mason+json"})
        assert resp.status_code == 200
        
    def _check_control_delete_method(self, ctrl, client, obj):
        """
        Tests a control for a DELETE method by sending a new DELETE request to
        the URI in the control's "href" attribute. If *CONFIRM_DELETE* is True,
        will also follow with a GET request, expecting 404 response code.
        """
    
        href = obj["@controls"][ctrl]["href"]
        method = obj["@controls"][ctrl]["method"].lower()
        assert method == "delete"
        resp = client.delete(href)
        assert resp.status_code == 204
        if self.CONFIRM_DELETE:
            resp = client.get(href)
            assert resp.status_code == 404
        
    def _check_control_post_method(self, ctrl, client, obj):
        """
        Tests a control for a POST method by sending a new POST request to
        the URI in the control's "href" attribute. Validates that the
        "encoding" and "method" attributes have correct values. Also validates
        the request body obtained from *valid_item_json* against the schema
        object in the control. Finally checks that sending a valid request will
        result in 201 response code.
        """
    
        ctrl_obj = obj["@controls"][ctrl]
        href = ctrl_obj["href"]
        method = ctrl_obj["method"].lower()
        encoding = ctrl_obj["encoding"].lower()
        schema = ctrl_obj["schema"]
        assert method == "post"
        assert encoding == "json"
        body = self.valid_item_json()
        validate(body, schema)
        resp = client.post(href, json=body)
        assert resp.status_code == 201

    def _check_control_put_method(self, ctrl, client, obj):
        """
        Tests a control for a PUT method by sending a new PUT request to
        the URI in the control's "href" attribute. Validates that the
        "encoding" and "method" attributes have correct values. Also validates
        the request body obtained from *valid_json* against the schema object
        in the control. Finally checks that sending a valid request will result
        in 201 response code.
        """

        ctrl_obj = obj["@controls"][ctrl]
        href = ctrl_obj["href"]
        method = ctrl_obj["method"].lower()
        encoding = ctrl_obj["encoding"].lower()
        schema = ctrl_obj["schema"]
        assert method == "put"
        assert encoding == "json"
        body = self.valid_json()
        validate(body, schema)
        resp = client.put(href, json=body)
        assert resp.status_code == 204

@pytest.fixture
def client():
    """
    Pytest fixture for setting up an app using a temporary SQLite database
    file. Populates the database with test data and yields the test client to
    be used in the each test.
    """

    db_fd, db_fname = tempfile.mkstemp()
    config = {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + db_fname,
        "TESTING": True
    }
    
    app = create_app(config)
    
    with app.app_context():
        db.create_all()
        populate_db()
        
    yield app.test_client()
    
    db.session.remove()
    os.close(db_fd)
    os.unlink(db_fname)
    
def _random_map(i):
    """
    Creates a map with random width and height.
    """
    
    return Map(
        name=f"Test Map {i}",
        slug=f"test-map-{i}",
        width=random.randint(10, 50),
        height=random.randint(10, 50),
    )
    
def _random_observer(i, w, h):
    """
    Creates an observer at a random position with a map of *w* width and *h*
    height. The position's availability is not checked in any way.
    """
    
    return Observer(
        name=f"Test Observer {i}",
        slug=f"test-observer-{i}",
        x=random.randint(1, w - 2),
        y=random.randint(1, h - 2),
        vision=(None, round(random.random() * 100, 2))[random.randint(0, 1)]
    )
    
def _random_obstacle(w, h):
    """
    Creates an obstacle at a random position with a map of *w* width and *h*
    height. The position's availability is not checked in any way.
    """

    return Obstacle(
        x=random.randint(1, w - 2),
        y=random.randint(1, h - 2),
    )
    
def populate_db():
    """
    Populates the database with one fixed map with one fixed observer and
    obstacle each, and one random of each. Also creates 3 random empty maps. 
    """

    fixed_map = Map(
        name="Test Map 1",
        slug="test-map-1",
        width=50,
        height=40,
    )
    fixed_observer = Observer(
        name="Test Observer 1",
        slug="test-observer-1",
        x=0,
        y=0,
        vision=5.0
    )
    fixed_obstacle = Obstacle(
        x=49,
        y=39
    )
    fixed_map.observers.append(fixed_observer)
    fixed_map.obstacles.append(fixed_obstacle)
    fixed_map.observers.append(_random_observer(2, 50, 40))
    fixed_map.obstacles.append(_random_obstacle(50, 40))
    db.session.add(fixed_map)

    for i in range(2, 4):
        map = _random_map(i)
        db.session.add(map)
    db.session.commit()
    
