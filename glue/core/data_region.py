import numpy as np
import shapely

from glue.core.data import Data
from glue.core.contracts import contract

from glue.core.component import Component, ExtendedComponent


__all__ = ['RegionData']


class RegionData(Data):
    """
    A glue Data object for storing data that is associated with a region.

    This object can be used when a dataset describes 2D regions or 1D ranges. It
    contains exactly one :class:`~glue.core.component.ExtendedComponent` object
    which contains the boundaries of the regions, and must also contain
    one or two components that give the center of the regions in whatever data
    coordinates the regions are described in. Links in glue are not made
    directly on the :class:`~glue.core.component.ExtendedComponent`, but instead
    on the center components.

    Thus, a subset that includes the center of a region will include that region,
    but a subset that includes just a little part of the region will not include
    that region. These center components are not the same pixel components. For
    example, a dataset that is a table of 2D regions will have a single
    :class:`~glue.core.component.CoordinateComponent`, but must have two of these center
    components.

    A typical use case for this object is to store the properties of geographic
    regions, where the boundaries of the regions are stored in an
    :class:`~glue.core.component.ExtendedComponent` and the centers of the
    regions are stored in two components, one for the longitude and one for the
    latitude. Additional components may describe arbitrary properties of these
    geographic regions (e.g. population, area, etc).

    This class is mostly a convenience class. Data Loaders can create RegionData
    directly from an iterable of geometries, since this class deals with
    creating representative points. Viewers can assume that when adding
    a RegionData object they are probably being asked to visualize the
    ExtendedComponent, and this class provide some convenience methods for
    use in reasoning about whether the components currently visualized
    in a Viewer are the correct ones to enable display of the ExtendedComponent.


    Parameters
    ----------
    label : `str`, optional
        The label of the data.
    coords : :class:`~glue.core.coordinates.Coordinates`, optional
        The coordinates associated with the data.
    **kwargs
        All other keyword arguments are passed to the :class:`~glue.core.data.Data`
        constructor.

    Attributes
    ----------
    extended_component_id : :class:`~glue.core.component_id.ComponentID`
        The ID of the :class:`~glue.core.component.ExtendedComponent` object
        that contains the boundaries of the regions.
    center_x_id : :class:`~glue.core.component_id.ComponentID`
        The ID of the Component object that contains the x-coordinate of the
        center of the regions. This is actually stored in the component
        with the extended_component_id, but it is convenient to have it here.
    center_y_id : :class:`~glue.core.component_id.ComponentID`
        The ID of the Component object that contains the y-coordinate of the
        center of the regions. This is actually stored in the component
        with the extended_component_id, but it is convenient to have it here.

    Examples
    --------

    There are two main options for initializing a :class:`~glue.core.data_region.RegionData`
    object. The first is to simply pass in a list of ``Shapely.Geometry`` objects
    with dimesionality N, from which we will create N+1 components: one
    :class:`~glue.core.component.ExtendedComponent` with the boundaries, and N
    regular Component(s) with the center coordinates computed from the Shapley
    method :meth:`~shapely.GeometryCollection.representative_point`:

        >>> geometries = [shapely.geometry.Point(0, 0).buffer(1), shapely.geometry.Point(1, 1).buffer(1)]
        >>> my_region_data = RegionData(label='My Regions', boundary=geometries)

    This will create a :class:`~glue.core.data_region.RegionData` object with three
    components: one :class:`~glue.core.component.ExtendedComponent` with label
    "geo" and two regular Components with labels "Center [x] for boundary"
    and "Center [y] for boundary".

    The second is to explicitly create an :class:`~glue.core.component.ExtendedComponent`
    (which requires passing in the ComponentIDs for the center coordinates) and
    then use `add_component` to add this component to a :class:`~glue.core.data_region.RegionData`
    object. You might use this approach if your dataset already contains points that
    represent the centers of your regions and you want to avoid re-calculating them. For example:

        >>> center_x = [0, 1]
        >>> center_y = [0, 1]
        >>> geometries = [shapely.geometry.Point(0, 0).buffer(1), shapely.geometry.Point(1, 1).buffer(1)]

        >>> my_region_data = RegionData(label='My Regions')
        >>> # Region IDs are created and returned when we add a Component to a Data object
        >>> cen_x_id = my_region_data.add_component(center_x, label='Center [x]')
        >>> cen_y_id = my_region_data.add_component(center_y, label='Center [y]')
        >>> extended_comp = ExtendedComponent(geometries, center_comp_ids=[cen_x_id, cen_y_id])
        >>> my_region_data.add_component(extended_comp, label='boundaries')

    """

    def __init__(self, label="", coords=None, **kwargs):
        self._extended_component_id = None
        # __init__ calls add_component which deals with ExtendedComponent logic
        super().__init__(label=label, coords=coords, **kwargs)

    def __repr__(self):
        return f'RegionData (label: {self.label} | extended_component: {self.extended_component_id})'

    @property
    def center_x_id(self):
        return self.get_component(self.extended_component_id).x

    @property
    def center_y_id(self):
        return self.get_component(self.extended_component_id).y

    @property
    def extended_component_id(self):
        return self._extended_component_id

    @contract(component='component_like', label='cid_like')
    def add_component(self, component, label):
        """ Add a new component to this data set, allowing only one :class:`~glue.core.component.ExtendedComponent`

        If component is an array of Shapely objects then we use
        :meth:`~shapely.GeometryCollection.representative_point`: to
        create two new components for the center coordinates of the regions and
        add them to the :class:`~glue.core.data_region.RegionData` object as well.

        If component is an :class:`~glue.core.component.ExtendedComponent`,
        then we simply add it to the :class:`~glue.core.data_region.RegionData` object.

        We do this here instead of extending ``Component.autotyped`` because
        we only want to use :class:`~glue.core.component.ExtendedComponent` objects
        in the context of a :class:`~glue.core.data_region.RegionData` object.

        Parameters
        ----------
        component : :class:`~glue.core.component.Component` or array-like
            Object to add. If this is an array of Shapely objects, then we
            create two new components for the center coordinates of the regions
            as well.
        label : `str` or :class:`~glue.core.component_id.ComponentID`
              The label. If this is a string, a new
              :class:`glue.core.component_id.ComponentID`
              with this label will be created and associated with the Component.

        Raises
        ------
           `ValueError`, if the :class:`~glue.core.data_region.RegionData` already has an extended component
        """

        if not isinstance(component, Component):
            if all(isinstance(s, shapely.Geometry) for s in component):
                center_x = []
                center_y = []
                for s in component:
                    rep = s.representative_point()
                    center_x.append(rep.x)
                    center_y.append(rep.y)
                cen_x_id = super().add_component(np.asarray(center_x), f"Center [x] for {label}")
                cen_y_id = super().add_component(np.asarray(center_y), f"Center [y] for {label}")
                ext_component = ExtendedComponent(np.asarray(component), center_comp_ids=[cen_x_id, cen_y_id])
                self._extended_component_id = super().add_component(ext_component, label)
                return self._extended_component_id

        if isinstance(component, ExtendedComponent):
            if self.extended_component_id is not None:
                raise ValueError(f"Cannot add another ExtendedComponent; existing extended component: {self.extended_component_id}")
            else:
                self._extended_component_id = super().add_component(component, label)
                return self._extended_component_id
        else:
            return super().add_component(component, label)

    def get_transform_to_cid(self, axis, other_cid):
        """
        Return the function that maps one of the center components to a different component.

        We can use this to get the transformation from the x,y coordinates
        that the ExtendedComponent are in to x and y attributes that are
        visualized in a Viewer so that we can translate the geometries
        in the ExtendedComponent to the new coordinates before displaying them.

        Parameters
        ----------
        axis : str
            Either 'x' or 'y'.
        other_cid : :class:`~glue.core.component.ComponentID`
            The other ComponentID (typically the one that is
            visualized in a Viewer).

        Returns
        -------
        func : `callable`
            The function that converts this_cid to other_cid which can then
            be used to transform the geometries before display.

        Raises
        ------
        ValueError
            If axis is not 'x' or 'y'.
        """
        if axis == 'x':
            this_cid = self.center_x_id
        elif axis == 'y':
            this_cid = self.center_y_id
        else:
            raise ValueError("axis must be 'x' or 'y'")
        func = None
        link = self._get_external_link(other_cid)
        if this_cid in link.get_from_ids():
            func = link.get_using()
        elif this_cid in link.get_to_ids():
            func = link.get_inverse()
        if func:
            return func
        else:
            return None

    def check_if_can_display(self, target_cid):
        """
        Check if target_cid can be mapped to one of the center components.

        If target_cid is one of the center components, then we can display
        the ExtendedComponent in a Viewer.

        Parameters
        ----------
        target_cid : :class:`~glue.core.component.ComponentID`
            The ComponentID (typically displayed in a Viewer) which we
            want to check if it is one of the special center components.

        Returns
        -------
        bool
            True if target_cid can be mapped to one of the center components, False otherwise.
        """
        from glue.core.link_manager import is_equivalent_cid  # avoid circular import

        center_cids = [self.center_x_id, self.center_y_id]
        for center_cid in center_cids:
            if is_equivalent_cid(self, center_cid, target_cid):
                return True
        else:
            link = self._get_external_link(target_cid)
            if not link:
                return False
            for center_cid in center_cids:
                if center_cid in link:
                    return True
            else:
                return False
