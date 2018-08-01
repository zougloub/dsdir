#!/usr/bin/env python
# -*- coding: utf-8 vi:noet
# dsdir yaml io

import sys, re, os, copy, collections
from collections import OrderedDict

import yaml

from .. import LazyPprintStr


def represent_ordereddict(self, data):
	return self.represent_mapping('tag:yaml.org,2002:map', data.items())

class DefaultOrderedDict(OrderedDict):
	# Source: http://stackoverflow.com/a/6190500/562769
	def __init__(self, default_factory=None, *a, **kw):
		if default_factory is not None \
		 and not isinstance(default_factory, collections.Callable):
			raise TypeError('first argument must be callable')
		OrderedDict.__init__(self, *a, **kw)
		self.default_factory = default_factory

	def __getitem__(self, key):
		try:
			return OrderedDict.__getitem__(self, key)
		except KeyError:
			return self.__missing__(key)

	def __missing__(self, key):
		if self.default_factory is None:
			raise KeyError(key)
		self[key] = value = self.default_factory()
		return value

	def __reduce__(self):
		if self.default_factory is None:
			args = tuple()
		else:
			args = self.default_factory,
		return type(self), args, None, None, self.items()

	def copy(self):
		return self.__copy__()

	def __copy__(self):
		return type(self)(self.default_factory, self)

	def __deepcopy__(self, memo):
		import copy
		return type(self)(self.default_factory,
						  copy.deepcopy(self.items()))

	def __repr__(self):
		return 'OrderedDefaultDict(%s, %s)' % (self.default_factory,
		 OrderedDict.__repr__(self))



def construct_yaml_map(self, node):
	data = OrderedDict()
	yield data
	value = self.construct_mapping(node)
	data.update(value)

def construct_mapping(self, node, deep=False):
	if isinstance(node, yaml.MappingNode):
		self.flatten_mapping(node)
	else:
		msg = 'expected a mapping node, but found %s' % node.id
		raise yaml.constructor.ConstructError(None, None, msg, node.start_mark)

	mapping = OrderedDict()
	for key_node, value_node in node.value:
		key = self.construct_object(key_node, deep=deep)
		try:
			hash(key)
		except TypeError as err:
			raise yaml.constructor.ConstructError(
				'while constructing a mapping', node.start_mark,
				'found unacceptable key (%s)' % err, key_node.start_mark)
		value = self.construct_object(value_node, deep=deep)
		mapping[key] = value
	return mapping

def construct_dsdir(self, node):
	data = OrderedDict()
	yield data
	value = self.construct_mapping(node)
	data.update(value)

class Loader(yaml.Loader):
	def __init__(self, *args, **kwargs):
		yaml.Loader.__init__(self, *args, **kwargs)

		self.add_constructor('tag:yaml.org,2002:map', type(self).construct_yaml_map)
		self.add_constructor('tag:yaml.org,2002:omap', type(self).construct_yaml_map)
		self.add_constructor('!dsdir', type(self).construct_dsdir)

	construct_yaml_map = construct_yaml_map
	construct_mapping = construct_mapping
	construct_dsdir = construct_dsdir


def represent_ordereddict(self, data):
	return self.represent_mapping('tag:yaml.org,2002:map', data.items())

def represent_dsdir(self, data):
	return self.represent_mapping('!dsdir', data.items())

class YamlDsDir(OrderedDict):
	pass

class Dumper(yaml.Dumper):
	def __init__(self, *args, **kwargs):
		yaml.Dumper.__init__(self, *args, **kwargs)
		self.add_representer(OrderedDict, type(self).represent_ordereddict)
		self.add_representer(YamlDsDir, type(self).represent_dsdir)

	represent_ordereddict = represent_ordereddict
	represent_dsdir = represent_dsdir



def to_yaml_struct(dsdir, tree, is_root=False):
	outer = collections.OrderedDict()
	inner = collections.OrderedDict()

	name = tree["name"]
	if tree["type"] == "folder":
		name += "/"

	if not is_root:
		outer[name] = inner
	else:
		outer = inner

	if "size" in tree:
		inner["size"] = tree["size"]


	hashes = collections.OrderedDict()
	for htype in dsdir._hash_dirs:
		hval = tree[htype]
		hashes[htype] = hval
		if hashes:
			inner["hash"] = hashes

	if tree.get("contents"):
		contents = []

		for idx_content, content in enumerate(tree.get("contents", [])):
			sub = to_yaml_struct(dsdir, content)
			contents.append(sub)
		else:
			inner["contents"] = contents

	return outer

def to_yaml(dsdir, tree):
	tree2 = copy.deepcopy(tree)
	y = to_yaml_struct(dsdir, tree2, is_root=True)
	y = YamlDsDir(y)
	return yaml.dump(y, Dumper=Dumper).encode("utf-8")


def validate_yaml(dsdir, f, validate_schema=True):

	errors = list()

	doc = yaml.load(f, Loader=Loader)

	if validate_schema:
		pass

	tree = from_yaml(dsdir, doc)

	dsdir._log.info("Internal representation: %s", LazyPprintStr(tree))

	errors = dsdir.validate_folder(tree)

	return errors


def from_yaml(dsdir, elem, path="."):

	out = dict()

	if 1:
		if path == ".":
			name = ".~"
		else:
			name = list(elem.keys())[0]
			elem = elem[name]
		out["name"] = name[:-1] if "contents" in elem else name
		out["path"] = os.path.join(path, out["name"])

	if "contents" in elem:
		out["type"] = "folder"
		out["contents"] = [ from_yaml(dsdir, x, out["path"]) for x in elem["contents"] ]
	else:
		out["type"] = "file"

	if "hash" in elem:
		hashes = elem["hash"]
		for htype, hval in hashes.items():
			out[htype] = hval

	return out
