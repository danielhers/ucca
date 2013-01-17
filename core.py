"""This module encapsulate the basic elements of the UCCA annotation.

A UCCA annotation is practically a directed acyclic graph (DAG), which
represents a :class:Passage of text and its annotation. The annotation itself
is divided into :class:Layer objects, where in each layer :class:Node objects
are connected between themselves and to Nodes in other layers using
:class:Edge objects.

"""

import operator
import functools


# Max number of digits allowed for a unique ID
UNIQUE_ID_MAX_DIGITS = 5


# Used as the default ordering key function for ordered objects, namely
# :class:Layer and :class:Node .
def id_orderkey(node):
    """Key function which sorts by layer (string), then by unique ID (int).

    Args:
        node: :class:Node which we will to sort according to its ID

    Returns:
        a string with the layer and unique ID in such a way that sort will
        first order lexicography the layer ID then numerically the unique ID.

    """
    layer, unique = node.ID.split(Node.ID_SEPARATOR)
    return "{} {:>{}}".format(layer, unique, UNIQUE_ID_MAX_DIGITS)


def edge_id_orderkey(edge):
    """Key function which sorts Edges by its IDs (using :func:id_orderkey).

    Args:
        edge: :class:Edge which we wish to sort according to the ID of its
        parent and children after using :func:id_orderkey.

    Returns:
        a string with the layer and unique ID in such a way that sort will
        first order lexicography the layer ID then numerically the unique ID.

    """
    return Edge.ID_FORMAT.format(id_orderkey(edge.parent),
                                 id_orderkey(edge.child))


class UCCAError(Exception):
    """Base class for all UCCA package exceptions."""
    pass


class FrozenPassageError(UCCAError):
    """Exception raised when trying to modify a frozen :class:Passage."""
    pass


class DuplicateIdError(UCCAError):
    """Exception raised when trying to add an element with an existing ID.

    For each element, a unique ID must be assiged. If the ID of the new element
    is already present in the :class:Passage in some way, this exception is
    raised.

    """
    pass


class MissingNodeError(UCCAError):
    """Exception raised when trying to access a non-existent :class:Node."""
    pass


class ModifyPassage:
    """Decorator for changing a :class:Passage or any member of it.

    This decorator is mandatory for anything which causes the elements in
    a :class:Passage to change by adding or removing an element, or changing
    an attribute.

    It validates that the Passage is not frozen before allowing the change.

    The decorator can't be used for __init__ calls, as at the stage of the
    check there are no instance attributes to check. So in such cases,
    a function that binds the object created with the Passage should be
    decorated instead (and should be called after the instance attributes
    are set).

    Attributes:
        fn: the function object to decorate

    """

    def __init__(self, fn):
        self.fn = fn

    def __get__(self, obj, cls):
        """Used to bind the function to the instance (add 'self')."""
        return functools.partial(self.__call__, obj)

    def __call__(self, *args, **kwargs):
        """Decorating functions which modify :class:Passage elements.

        Args:
            args: list of all arguments, assuming the first is the object
                which modifies :class:Passage, and it has an attribute root
                which points to the Passage it is part of.
            kwargs: list of all keyword arguments

        Returns:
            The decorated function result.

        Raises:
            FrozenPassageError: if the :class:Passage is frozen and can't be
                modified.

        """
        @functools.wraps(self.fn)
        def decorated(*args, **kwargs):
            if args[0].root.frozen:
                raise FrozenPassageError()
            self.fn(*args, **kwargs)
        return decorated(*args, **kwargs)


class _AttributeDict:
    """Dictionary which stores attributes for any UCCA element.

    This dictionary is used to store attributes which are part of any
    element in the UCCA annotation scheme. It's advantage over regular
    dictionary is adhering to :class:Passage frozen status and modification
    decorators.

    Attributes:
        root: the Passage this object is linked with

    """

    def __init__(self, root, mapping=None):
        self._root = root
        self._dict = mapping.copy() if mapping is not None else dict()

    def __getitem__(self, key):
        return self._dict[key]

    def get(self, key, default=None):
        return self._dict.get(key, default)

    @property
    def root(self):
        return self._root

    def copy(self):
        return self._dict.copy()

    @ModifyPassage
    def __setitem__(self, key, value):
        self._dict[key] = value

    @ModifyPassage
    def __delitem__(self, key):
        del self._dict[key]

    def __len__(self):
        return len(self._dict)


class Edge:
    """Labeled edge between two :class:Node objects in UCCA annotation graph.

    An edge between Nodes in a :class:Passage is a simple object; it is a
    directed edge whose ID is derived by the parent and child of the edge,
    it is mostly immutable except for its attributes, and it is labeled with
    the connection type between the Nodes.

    Attributes:
        ID: ID of the Edge, constructed from the IDs of the two Nodes
        root: the Passage this object is linked with
        attrib: attribute dictionary of the Edge
        extra: temporary storage space for undocumented attribues and data
        tag: the string label of the Edge
        parent: the originating Node of the Edge
        child: the target Node of the Edge
        ID_FORMAT: format string which creates the ID of the Edge from
            the IDs of the parent (first argument to the formattinf string)
            and the child (second argument).

    """

    ID_FORMAT = "{}->{}"

    def __init__(self, root, tag, parent, child, attrib=None):
        """Creates a new :class:Edge object.

        Args:
            see :class:Edge documentation.

        Raises:
            FrozenPassageError: if the :class:Passage object we are part of
                is frozen and can't be modified.

        """
        if root.frozen:
            raise FrozenPassageError()
        self._tag = tag
        self._root = root
        self._parent = parent
        self._child = child
        self._attrib = _AttributeDict(root, attrib)
        self.extra = {}

    @property
    def tag(self):
        return self._tag

    @property
    def root(self):
        return self._root

    @property
    def parent(self):
        return self._parent

    @property
    def child(self):
        return self._child

    @property
    def attrib(self):
        return self._attrib

    @property
    def ID(self):
        return Edge.ID_FORMAT.format(self._parent.ID, self._child.ID)


class Node:
    """Labeled Node in UCCA annotation graph.

    A Node in :class:Passage UCCA annotation is an vertex in the annotation
    graph, which may be an internal vertex or a leaf, and is labeled with a
    tag that specifies both the :class:Layer it belongs to and it's ID in this
    Layer. It can have multiple children Nodes through :class:Edge objects,
    and these children are ordered according to an internal order function.

    Attributes:
        ID: ID of the Node, constructed from the ID of the Layer it belongs to,
            a separator, and a unique alphanumeric ID in the layer.
        root: the Passage this object is linked with
        attrib: attribute dictionary of the Node
        extra: temporary storage space for undocumented attribues and data
        tag: the string label of the Node
        layer: the Layer this Node belongs to
        parents: the Nodes which have incoming Edges to this object
        children: the Nodes which have outgoing Edges from this object
        orderkey: the key function for ordering the outgoing Edges
        ID_SEPARATOR: separator function between the Layer ID and the unique
            Node ID in the complete ID of the Node. Mustn't be alphanumeric.

    """

    ID_SEPARATOR = '.'

    def __init__(self, ID, root, tag, attrib=None, *,
                 orderkey=edge_id_orderkey):
        """Creates a new :class:Node object.

        Args:
            see :class:Node documentation.

        Raises:
            FrozenPassageError: if the :class:Passage object we are part of
                is frozen and can't be modified.

        """
        if root.frozen:
            raise FrozenPassageError()
        self._tag = tag
        self._root = root
        self._ID = ID
        self._attrib = _AttributeDict(root, attrib)
        self.extra = {}
        self._outgoing = []
        self._incoming = []
        self._orderkey = orderkey

        # After properly initializing self, add it to the Passage/Layer
        root._add_node(self)
        root.layer(self.layer.ID)._add_node(self)

    @property
    def tag(self):
        return self._tag

    @property
    def root(self):
        return self._root

    @property
    def ID(self):
        return self._ID

    @property
    def attrib(self):
        return self._attrib

    @property
    def layer(self):
        return self._root.layer(self._ID.split(Node.ID_SEPARATOR)[0])

    @property
    def parents(self):
        return [edge.parent for edge in self._incoming]

    @property
    def children(self):
        return [edge.child for edge in self._outgoing]

    def __bool__(self):
        return True

    def __len__(self):
        return len(self._outgoing)

    def __getitem__(self, index):
        return self._outgoing[index]

    @ModifyPassage
    def add(self, edge_tag, node, *, edge_attrib=None):
        """Adds another :class:Node object as a child of self.

        Args:
            edge_tag: the label of the :class:Edge connecting between the
                Nodes
            node: the Node object which we want to have an Edge to
            edge_attrib: Keyword only, dictionary of attributes to be passed
                to the Edge initializer.

        Raises:
            FrozenPassageError: if the :class:Passage object we are part of
                is frozen and can't be modified.

        """
        edge = Edge(root=self._root, tag=edge_tag, parent=self,
                    child=node, attrib=edge_attrib)
        self._outgoing.append(edge)
        self._outgoing.sort(key=self._orderkey)
        node._incoming.append(edge)
        node._incoming.sort(key=node._orderkey)
        if self.layer == node.layer:
            self.layer._add_edge(edge)

    @ModifyPassage
    def remove(self, edge_or_node):
        """Removes the :class:Edge between self and a child :class:Node.

        This methods removes the Edge given, or the Edge connecting self and
        the Node given, from the annotation of :class:Passage. It does not
        remove the target or originating Node from the graph but just unlinks
        them.

        Args:
            edge_or_node: either an Edge or Node object to remove/unlink

        Raises:
            MissingNodeError: if the Node or Edge is not connected with self.

        """
        if edge_or_node not in self._outgoing:  # a Node, or an error
            try:
                edge = [edge for edge in self._outgoing
                        if edge.child == edge_or_node][0]
            except IndexError:
                raise MissingNodeError()
        else:  # an Edge object
            edge = edge_or_node

        try:
            self._outgoing.remove(edge)
            edge.child._incoming.remove(edge)
            if self.layer == edge.child.layer:
                self.layer._remove_edge(edge)
        except ValueError:
            raise MissingNodeError()

    @property
    def orderkey(self):
        return self._orderkey

    @orderkey.setter
    def orderkey(self, value):
        self._orderkey = value
        self._outgoing.sort(key=value)

    @ModifyPassage
    def destroy(self):
        """Removes the :class:Node from the :class:Passage annotation graph.

        This method unlinks self from all other :class:Node objects and removes
        self from the :class:Layer and Passage objects.

        """
        for edge in self._outgoing:
            self.remove(edge)
        for edge in self._incoming:
            edge.parent.remove(edge)
        self.layer._remove_node(self)
        self._root._remove_node(self)


class Layer:
    """Group of similar :class:Node objects in UCCA annotation graph.

    A Layer in UCCA annotation graph is a subgraph of the whole :class:Passage
    annotation graph which consists of similar Nodes and :class:Edge objects
    between them. The Nodes and the Layer itself has some formal definition for
    being grouped togehter.

    Attributes:
        ID: ID of the Layer, must be alphanumeric.
        root: the Passage this object is linked with
        attrib: attribute dictionary of the Layer
        extra: temporary storage space for undocumented attribues and data
        orderkey: the key function for ordering the Nodes in the layer.
            Note that it must rely only on the Nodes and/or Edges in the Layer.
            If it, for example, rely on Edges added between Nodes in the Layer
            and Nodes outside the Layer (hence, the Edges are not in the Layer)
            the order will not be updated (because the Layer object won't know
            that something has changed).
        all: a list of all the Nodes which are part of this Layer
        heads: a list of all Nodes which have no incoming Edges in the subgraph
            of the Layer (can have Edges from Nodes in other Layers).

    """

    def __init__(self, ID, root, attrib=None, *, orderkey=id_orderkey):
        """Creates a new :class:Layer object.

        Args:
            see :class:Layer documentation.

        Raises:
            FrozenPassageError: if the :class:Passage object we are part of
                is frozen and can't be modified.

        """
        if root.frozen:
            raise FrozenPassageError()
        self._ID = ID
        self._root = root
        self._attrib = _AttributeDict(root, attrib)
        self.extra = {}
        self._all = []
        self._heads = []
        self._orderkey = orderkey
        root._add_layer(self)

    @property
    def ID(self):
        return self._ID

    @property
    def root(self):
        return self._root

    @property
    def attrib(self):
        return self._attrib

    @property
    def all(self):
        return self._all[:]

    @property
    def heads(self):
        return self._heads[:]

    @property
    def orderkey(self):
        return self._orderkey

    @orderkey.setter
    def orderkey(self, value):
        self._orderkey = value
        self._all.sort(key=value)
        self._heads.sort(key=value)

    def _add_edge(self, edge):
        """Alters self.heads if an :class:Edge has been added to the subgraph.

        Should be called when both :class:Node objects of the edge are part
        of this Layer (and hence part of the subgraph of it).

        Args:
            edge: the Edge added to the Layer subgraph

        """
        if edge.child in self._heads:
            self._heads.remove(edge.child)
        # Order may depend on edges, so re-order
        self._all.sort(key=self._orderkey)
        self._heads.sort(key=self._orderkey)

    def _remove_edge(self, edge):
        """Alters self.heads if an :class:Edge has been removed.

        Should be called when both :class:Node objects of the edge are part
        of this Layer (and hence part of the subgraph of it).

        Args:
            edge: the Edge removed from the Layer subgraph

        """
        if all(p.layer != edge.child.layer for p in edge.child.parents):
            self._heads.append(edge.child)
            self._heads.sort(key=self._orderkey)
        # Order may depend on edges, so re-order
        self._all.sort(key=self._orderkey)
        self._heads.sort(key=self._orderkey)

    def _add_node(self, node):
        """Adds a :class:node to the :class:Layer.

        Assumes node has no incoming or outgoing :class:Edge objects.

        """
        self._all.append(node)
        self._all.sort(key=self._orderkey)
        self._heads.append(node)
        self._heads.sort(key=self._orderkey)

    def _remove_node(self, node):
        """Removes a :class:node from the :class:Layer.

        Assumes node has no incoming or outgoing :class:Edge objects.

        """
        self._all.remove(node)
        self._heads.remove(node)


class Passage:
    """An annotated text with UCCA annotatation graph.

    A Passage is an object representing a text annotated with UCCA annotation.
    UCCA annotation is a directed acyclic graph of :class:Node and :class:Edge
    objects grouped into :class:Layer objects.

    Attributes:
        ID: ID of the Passage
        root: simply self, for API similarity with other UCCA objects
        attrib: attribute dictionary of the Passage
        extra: temporary storage space for undocumented attribues and data
        layers: all Layers of the Passage, no order guaranteed
        frozen: indicates whether the Passage can be modified or not, boolean.

    """

    def __init__(self, ID, attrib=None):
        """Creates a new :class:Passage object.

        Args:
            see :class:Passage documentation.

        """
        self._ID = ID
        self._attrib = _AttributeDict(self, attrib)
        self.extra = {}
        self._layers = {}
        self._nodes = {}
        self.frozen = False

    @property
    def ID(self):
        return self._ID

    @property
    def root(self):
        return self

    @property
    def attrib(self):
        return self._attrib

    @property
    def layers(self):
        return self._layers.values()

    def layer(self, ID):
        """Returns the :class:Layer object whose ID is given.

        Args:
            ID: ID of the Layer requested.

        Raises:
            KeyError: if no Layer with this ID is present

        """
        return self._layers[ID]

    @ModifyPassage
    def _add_layer(self, layer):
        """Adds a :class:Layer object to the :class:Passage.

        Args:
            layer: the Layer object to add

        Raises:
            DuplicateIdError: if layer.ID is identical to a Layer already
                present in the Passage.
            FrozenPassageError: if the :class:Passage object we are part of
                is frozen and can't be modified.

        """
        if layer.ID in self._layers:
            raise DuplicateIdError()
        self._layers[layer.ID] = layer

    @ModifyPassage
    def _add_node(self, node):
        """Adds a :class:Node object to the :class:Passage.

        Args:
            node: the Node object to add

        Raises:
            DuplicateIdError: if node.ID is identical to a Node already
                present in the Passage.
            FrozenPassageError: if the :class:Passage object we are part of
                is frozen and can't be modified.

        """
        if node.ID in self._nodes:
            raise DuplicateIdError()
        self._nodes[node.ID] = node

    def _remove_node(self, node):
        """Removes a :class:Node object from the :class:Passage.

        Args:
            node: the Node object to remove, must be unlinked with any other
                Node objects and removed from its :class:Layer.

        Raises:
            KeyError: if no Node with this ID is present

        """
        del self._nodes[node.ID]
