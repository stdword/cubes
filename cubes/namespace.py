# -*- coding: utf-8 -*-

from __future__ import absolute_import

__all__ = [
    "Namespace",
]

class Namespace(object):
    def __init__(self):
        self.namespaces = {}
        self.providers = []
        self.objects = {}

    def namespace(self, path, create=False):
        """Returns a tuple (`namespace`, `remainder`) where `namespace` is
        the deepest namespace in the namespace hierarchy and `remainder` is
        the remaining part of the path that has no namespace (is an object
        name or contains part of external namespace).

        If path is empty or not provided then returns self.
        """

        if not path:
            return (self, [])

        if isinstance(path, basestring):
            path = path.split(".")

        namespace = self
        found = False
        for i, element in enumerate(path):
            remainder = path[i+1:]
            if element in namespace.namespaces:
                namespace = namespace.namespaces[element]
                found = True
            else:
                remainder = path[i:]
                break

        if not create:
            return (namespace, remainder)
        else:
            for element in remainder:
                namespace = namespace.create_namespace(element)

            return (namespace, [])

    def create_namespace(self, name):
        """Create a namespace `name` in the receiver."""
        namespace = Namespace()
        self.namespaces[name] = namespace
        return namespace

    def namespace_for_cube(self, cube):
        """Returns a tuple (`namespace`, `relative_cube`) where `namespace` is
        a namespace conaining `cube` and `relative_cube` is a name of the
        `cube` within the `namespace`. For example: if cube is
        ``slicer.nested.cube`` and there is namespace ``slicer`` then that
        namespace is returned and the `relative_cube` will be ``nested.cube``"""

        cube = str(cube)
        split = cube.split(".")
        if len(split) > 1:
            path = split[0:-1]
            cube = split[-1]
        else:
            path = []
            cube = cube

        (namespace, remainder) = self.namespace(path)

        if remainder:
            relative_cube = "%s.%s" % (".".join(remainder), cube)
        else:
            relative_cube = cube

        return (namespace, relative_cube)

    def list_cubes(self, recursive=False):
        """Retursn a list of cube info dictionaries with keys: `name`,
        `label`, `description`, `category` and `info`."""

        all_cubes = []
        cube_names = set()
        for provider in self.providers:
            cubes = provider.list_cubes()
            # Cehck for duplicity
            for cube in cubes:
                name = cube["name"]
                if name in cube_names:
                    raise ModelError("Duplicate cube '%s'" % name)
                cube_names.add(name)

            all_cubes += cubes

        if recursive:
            for name, ns in self.namespaces.items():
                cubes = ns.list_cubes(recursive=True)
                for cube in cubes:
                    cube["name"] = "%s.%s" % (name, cube["name"])
                all_cubes += cubes

        return all_cubes

    def cube(self, name, locale=None, recursive=False):
        """Return cube named `name`.

        If `recursive` is ``True`` then look for cube in child namespaces.
        """
        cube = None

        for provider in self.providers:
            # TODO: use locale
            try:
                cube = provider.cube(name, locale)
            except NoSuchCubeError:
                pass
            else:
                cube.provider = provider
                break

        if not cube and recursive:
            for key, namespace in self.namespaces.items():
                try:
                    cube = namespace.cube(name, locale, recursive=True)
                except NoSuchCubeError:
                    # Just continue with sibling
                    pass
                else:
                    break

        if not cube:
            raise NoSuchCubeError("Unknown cube '%s'" % str(name), name)

        translation = self.translations.get(locale)

        if translation:
            return cube.localize(translation)
        else:
            return cube

    def dimension(self, name, locale=None, templates=None):
        dim = None

        # TODO: cache dimensions
        for provider in self.providers:
            # TODO: use locale
            try:
                dim = provider.dimension(name, locale=locale,
                                         templates=templates)
            except NoSuchDimensionError:
                pass
            else:
                return dim

        raise NoSuchDimensionError("Unknown dimension '%s'" % str(name), name)

    def add_provider(self, provider):
        self.providers.append(provider)

