from flask import url_for

class MasonBuilder(dict):
    """
    A convenience class for managing dictionaries that represent Mason
    objects. It provides nice shorthands for inserting some of the more
    elements into the object but mostly is just a parent for the much more
    useful subclass defined next. This class is generic in the sense that it
    does not contain any application specific implementation details.
    
    Note that child classes should set the *DELETE_RELATION* to the application
    specific relation name from the application namespace. The IANA standard
    does not define a link relation for deleting something.
    """

    DELETE_RELATION = ""

    def add_error(self, title, details):
        """
        Adds an error element to the object. Should only be used for the root
        object, and only in error scenarios.
        Note: Mason allows more than one string in the @messages property (it's
        in fact an array). However we are being lazy and supporting just one
        message.
        : param str title: Short title for the error
        : param str details: Longer human-readable description
        """

        self["@error"] = {
            "@message": title,
            "@messages": [details],
        }

    def add_namespace(self, ns, uri):
        """
        Adds a namespace element to the object. A namespace defines where our
        link relations are coming from. The URI can be an address where
        developers can find information about our link relations.
        : param str ns: the namespace prefix
        : param str uri: the identifier URI of the namespace
        """

        if "@namespaces" not in self:
            self["@namespaces"] = {}

        self["@namespaces"][ns] = {
            "name": uri
        }

    def add_control(self, ctrl_name, href, **kwargs):
        """
        Adds a control property to an object. Also adds the @controls property
        if it doesn't exist on the object yet. Technically only certain
        properties are allowed for kwargs but again we're being lazy and don't
        perform any checking.
        The allowed properties can be found from here
        https://github.com/JornWildt/Mason/blob/master/Documentation/Mason-draft-2.md
        : param str ctrl_name: name of the control (including namespace if any)
        : param str href: target URI for the control
        """

        if "@controls" not in self:
            self["@controls"] = {}

        self["@controls"][ctrl_name] = kwargs
        self["@controls"][ctrl_name]["href"] = href
        
    def add_control_post(self, ctrl_name, title, href, schema):
        """
        Utility method for adding POST type controls. The control is
        constructed from the method's parameters. Method and encoding are
        fixed to "POST" and "json" respectively.
        
        : param str ctrl_name: name of the control (including namespace if any)
        : param str href: target URI for the control
        : param str title: human-readable title for the control
        : param dict schema: a dictionary representing a valid JSON schema
        """
    
        self.add_control(
            ctrl_name,
            href,
            method="POST",
            encoding="json",
            title=title,
            schema=schema
        )

    def add_control_put(self, title, href, schema):
        """
        Utility method for adding PUT type controls. The control is
        constructed from the method's parameters. Control name, method and
        encoding are fixed to "edit", "PUT" and "json" respectively.
        
        : param str href: target URI for the control
        : param str title: human-readable title for the control
        : param dict schema: a dictionary representing a valid JSON schema
        """

        self.add_control(
            "edit",
            href,
            method="PUT",
            encoding="json",
            title=title,
            schema=schema
        )
        
    def add_control_delete(self, title, href):
        """
        Utility method for adding PUT type controls. The control is
        constructed from the method's parameters. Control method is fixed to
        "DELETE", and control's name is read from the class attribute
        *DELETE_RELATION* which needs to be overridden by the child class.

        : param str href: target URI for the control
        : param str title: human-readable title for the control
        """
        
        self.add_control(
            self.DELETE_RELATION,
            href,
            method="DELETE",
            title=title,
        )
        

class MapBuilder(MasonBuilder):
    """
    Application specific child class of MasonBuilder. Contains shorthand
    methods for adding various POST, PUT and DELETE methods to resource
    representations using Mason.
    """
    
    DELETE_RELATION = "pwp-map:delete"
    
    def add_control_create_map(self, schema):
        """
        Adds a control for creating a map using POST. The caller needs to
        provide the *schema*.
        """
    
        self.add_control_post(
            "pwp-map:create-map",
            "Create a new map",
            url_for("api.mapcollection"),
            schema
        )
        
    def add_control_edit_map(self, map, schema):
        """
        Adds a control for updating a map using PUT. The caller needs to
        provide the *schema*.
        """

        self.add_control_put(
            "Update this map",
            url_for("api.mapitem", map=map),
            schema
        )
        
    def add_control_delete_map(self, map):
        """
        Adds a control for deleting a map using DELETE.
        """
    
        self.add_control_delete(
            "Delete this map",
            url_for("api.mapitem", map=map),
        )
        
    def add_control_create_observer(self, map, schema):
        """
        Adds a control for placing a new observer on the given *map* using
        POST. The caller needs to provide the *schema*.
        """

        self.add_control_post(
            "pwp-map:create-observer",
            "Place a new observer on this map",
            url_for("api.mapobservers", map=map),
            schema
        )
        
    def add_control_create_obstacle(self, map, schema):
        """
        Adds a control for placing a new obstacle on the given *map* using
        POST. The caller needs to provide the *schema*.
        """

        self.add_control_post(
            "pwp-map:create-obstacle",
            "Place a new obstacle on this map",
            url_for("api.mapobstacles", map=map),
            schema
        )
    
    def add_control_edit_observer(self, observer, schema):
        """
        Adds a control to update the given observer using PUT. The caller needs
        to provide the *schema*.
        """
        
        self.add_control_put(
            "Update this observer",
            url_for("api.observeritem", map=observer.map, observer=observer),
            schema
        )
        
    def add_control_delete_observer(self, observer):
        """
        Adds a control for deleting an observer using DELETE.
        """

        self.add_control_delete(
            "Delete this observer",
            url_for("api.observeritem", map=observer.map, observer=observer),
        )
        
    def add_control_delete_obstacle(self, obstacle):
        """
        Adds a control for deleting an obstacle using DELETE.
        """

        self.add_control_delete(
            "Delete this obstacle",
            url_for(
                "api.obstacleitem",
                map=obstacle.map,
                x=obstacle.x,
                y=obstacle.y
            ),
        )
