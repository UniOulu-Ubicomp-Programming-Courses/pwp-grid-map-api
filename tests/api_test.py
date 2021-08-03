import json
from tests.utils import *
    

class TestMapCollection(JsonApiPostTestBase, MasonApiTestBase):
    
    RESOURCE_URL = "/api/maps/"
    ITEM_URL = "/api/maps/valid-map-a/"
    REQUIRED_FIELDS = ["name", "width", "height"]
    INVALID_VALUES = MAP_INVALID_VALUES
    TEST_UNIQUE = True
    VERIFY_ITEM = True
   
    def valid_item_json(self):
        return {
            "name": f"Valid Map A",
            "width": random.randint(10, 50),
            "height": random.randint(10, 50),
        }
        
    def test_get(self, client):
        resp = client.get(self.RESOURCE_URL, headers={"Accept": "application/json"})
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert len(body["maps"]) == 3
        for item in body["maps"]:
            assert "name" in item
            assert "slug" in item
            assert "width" in item
            assert "height" in item
            assert "observers" not in item
            assert "obstacles" not in item
            
    def test_mason_get(self, client):
        resp = client.get(self.RESOURCE_URL, headers={"Accept": "application/vnd.mason+json"})
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert "pwp-map" in body["@namespaces"]
        assert "profile" in body["@controls"]
        self._check_control_post_method("pwp-map:create-map", client, body)
        self._check_control_get_method("self", client, body)
        assert len(body["maps"]) == 3
        for item in body["maps"]:
            assert "name" in item
            assert "slug" in item
            assert "width" in item
            assert "height" in item
            assert "observers" not in item
            assert "obstacles" not in item
            self._check_control_get_method("self", client, item)
        

class TestMapItem(JsonApiPutTestBase, JsonApiDeleteTestBase, MasonApiTestBase):
    
    RESOURCE_URL = "/api/maps/test-map-1/"
    RESOURCE_2_URL = "/api/maps/test-map-2/"
    RELOCATED_URL = "/api/maps/valid-map-a/"
    REQUIRED_FIELDS = ["name", "width", "height"]
    INVALID_VALUES = MAP_INVALID_VALUES
    TEST_UNIQUE = True
    VERIFY_ITEM = True
    
    def valid_json(self):
        return {
            "name": f"Valid Map A",
            "width": random.randint(10, 50),
            "height": random.randint(10, 50),
        }
        
    def test_get(self, client):
        resp = client.get(self.RESOURCE_URL, headers={"Accept": "application/json"})
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert "name" in body
        assert "slug" in body
        assert "width" in body
        assert "height" in body
        assert "observers" in body
        assert "obstacles" in body
        assert isinstance(body["observers"], list)
        assert isinstance(body["obstacles"], list)

    def test_mason_get(self, client):
        resp = client.get(self.RESOURCE_URL, headers={"Accept": "application/vnd.mason+json"})
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert "name" in body
        assert "slug" in body
        assert "width" in body
        assert "height" in body
        assert "observers" in body
        assert "obstacles" in body
        assert "pwp-map" in body["@namespaces"]
        assert "profile" in body["@controls"]
        self._check_control_get_method("self", client, body)
        self._check_control_get_method("collection", client, body)
        for observer in body["observers"]:
            self._check_control_get_method("self", client, observer)
        for obstacle in body["obstacles"]:
            self._check_control_delete_method("pwp-map:delete", client, obstacle)
        
    def test_mason_put(self, client):
        resp = client.get(self.RESOURCE_URL, headers={"Accept": "application/vnd.mason+json"})
        body = json.loads(resp.data)
        self._check_control_put_method("edit", client, body)

    def test_mason_delete(self, client):
        resp = client.get(self.RESOURCE_URL, headers={"Accept": "application/vnd.mason+json"})
        body = json.loads(resp.data)
        self._check_control_delete_method("pwp-map:delete", client, body)


class TestMapObserverCollection(JsonApiPostTestBase, MasonApiTestBase):
    
    RESOURCE_URL = "/api/maps/test-map-1/observers/"
    ITEM_URL = "/api/maps/test-map-1/observers/valid-observer-a/"
    REQUIRED_FIELDS = ["name", "x", "y"]
    INVALID_VALUES = OBS_INVALID_VALUES
    TEST_UNIQUE = True
    VERIFY_ITEM = True
    
    def valid_item_json(self):
       return {
            "name": f"Valid Observer A",
            "x": random.randint(0, 9),
            "y": random.randint(0, 9),
        }
        
    def test_post_control(self, client):
        resp = client.get(
            TestMapItem.RESOURCE_URL,
            headers={"Accept": "application/vnd.mason+json"}
        )
        body = json.loads(resp.data)
        self._check_control_post_method("pwp-map:create-observer", client, body)
        
        
class TestMapObstacleCollection(JsonApiPostTestBase, MasonApiTestBase):

    RESOURCE_URL = "/api/maps/test-map-1/obstacles/"
    ITEM_URL = "/api/maps/test-map-1/obstacles/5/5/"
    REQUIRED_FIELDS = ["x", "y"]
    INVALID_VALUES = OBS_INVALID_VALUES
    TEST_UNIQUE = False
    VERIFY_ITEM = False
     
    def valid_item_json(self):
       return {
            "x": 5,
            "y": 5,
        }

    def test_post_control(self, client):
        resp = client.get(
            TestMapItem.RESOURCE_URL,
            headers={"Accept": "application/vnd.mason+json"}
        )
        body = json.loads(resp.data)
        self._check_control_post_method("pwp-map:create-obstacle", client, body)


class TestObserverItem(JsonApiPutTestBase, JsonApiDeleteTestBase, MasonApiTestBase):
    
    RESOURCE_URL = "/api/maps/test-map-1/observers/test-observer-1/"
    RESOURCE_2_URL = "/api/maps/test-map-1/observers/test-observer-2/"
    RELOCATED_URL = "/api/maps/test-map-1/observers/valid-observer-a/"
    REQUIRED_FIELDS = ["name", "x", "y"]
    INVALID_VALUES = OBS_INVALID_VALUES
    TEST_UNIQUE = True
    VERIFY_ITEM = True
    CONFIRM_DELETE = True
    
    def valid_json(self):
        return {
            "name": f"Valid Observer A",
            "x": random.randint(0, 9),
            "y": random.randint(0, 9),
        }
        
    def test_get(self, client):
        resp = client.get(self.RESOURCE_URL, headers={"Accept": "application/json"})
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert "name" in body
        assert "slug" in body
        assert "vision" in body
        assert "x" in body
        assert "y" in body

    def test_mason_get(self, client):
        resp = client.get(self.RESOURCE_URL, headers={"Accept": "application/vnd.mason+json"})
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert "name" in body
        assert "slug" in body
        assert "vision" in body
        assert "x" in body
        assert "y" in body
        assert "pwp-map" in body["@namespaces"]
        assert "profile" in body["@controls"]
        self._check_control_get_method("self", client, body)
        self._check_control_get_method("up", client, body)

    def test_mason_put(self, client):
        resp = client.get(self.RESOURCE_URL, headers={"Accept": "application/vnd.mason+json"})
        body = json.loads(resp.data)
        self._check_control_put_method("edit", client, body)

    def test_mason_delete(self, client):
        resp = client.get(self.RESOURCE_URL, headers={"Accept": "application/vnd.mason+json"})
        body = json.loads(resp.data)
        self._check_control_delete_method("pwp-map:delete", client, body)


class TestObstacleItem(JsonApiDeleteTestBase):

    RESOURCE_URL = "/api/maps/test-map-1/obstacles/49/39/"
