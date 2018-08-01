#!/usr/bin/env python
# -*- coding: utf-8 vi:noet
# dsdir management

import sys, io, os, re, hashlib, collections, codecs, logging, json


"""

Internally a dict-based internal representation is used, it looks like::

   {
	"type": "folder",
	"name": "",
	"contents": [
	 {
	  "name": "",
	 }
	]
   }


"""

all_hash_dirs = ("git-sha1",)
all_hash_files = ("sha1", "git-sha1")



class LazyPprintStr(object):
	def __init__(self, x):
		self.x = x
	def __str__(self):
		x = self.x
		if isinstance(x, dict):
			return json.dumps(x, indent=True)
		return str(x)


def rec_files(files_sel):
	"""
	Transform a list of files and directories into a list of files.
	"""
	files_out = list()
	for candidate in files_sel:
		if os.path.isfile(candidate):
			files_out.append(candidate)
		elif os.path.isdir(candidate):
			for cwd, dirs, files in os.walk(candidate):
				for filename in files:
					path = os.path.join(cwd, filename)
					files_out.append(path)
	files_out.sort()
	return files_out




def h_file(node, hnames, key_prefix=""):
	"""
	:param node: dict with a path
	:param hashes: iterable of file hash names
	:return: None
	"""

	path = node["path"]
	size = os.path.getsize(path)

	hashes = dict()
	for htype in hnames:
		if htype == "git-sha1":
			h = hashlib.sha1()
			h.update(("blob %d" % size).encode() + b"\0")
		else:
			h = getattr(hashlib, htype)()
		hashes[htype] = h

	if hashes != dict():
		with io.open(path, "rb") as f:
			for chunk in iter(lambda: f.read(4096), b""):
				for h in hashes.values():
					h.update(chunk)
			for hname, h in hashes.items():
				node[key_prefix + hname] = h.hexdigest()


def path_split(path, rest=[], sep=os.path.sep):
	"""
	:param path: path to be split
	:param rest: rest (used for recursion)
	:return: split path

	Examples:

	- "/a/b/c" ->  ("/", "a", "b", "c")
	- "a/b/c" ->  ("a", "b", "c")
	"""

	if path == "":
		return ""

	res = path.split(sep)
	if res[0] == "":
		res[0] = "/"
	return tuple(res)


def path_join(arg, sep=os.path.sep):
	"""
	:param arg: sequence of path elements (as path_split would make them)
	:return: path string
	"""

	if len(arg) > 1:
		if arg[0] == "/":
			return arg[0] + sep.join(arg[1:])
		elif arg[0] == "":
			return "." + sep + sep.join(arg[1:])
		else:
			return sep.join(arg)
	return arg[0]


def tree_add_paths(paths, tree, sep=os.path.sep):
	"""
	Transform a series of (top-down) paths into a hierarchy.
	:param paths: iterable of slash-separated strings
	:param tree: dictionary representing a tree. Leaves have None value.
	"""

	for path in paths:
		parts = path_split(path)

		if len(parts) == 1: # leaf
			tree[parts[0]] = None
		else:
			node, sub = parts[0], sep.join(parts[1:])
			if node not in tree:
				tree[node] = dict()
			tree_add_paths([sub], tree[node])


def common_prefix(paths):
	"""
	:param paths: paths
	:return: common prefix between paths
	"""
	if len(paths) <= 1:
		raise ValueError()
	
	#paths = set([ tuple(x.split(os.sep)) for x in paths ])
	paths = set([ path_split(x) for x in paths ])

	s1 = min(paths)
	s2 = max(paths)
	for i, c in enumerate(s1):
		if c != s2[i]:
			return path_join(s1[:i])
	return path_join(s1)


def h_tree(node, hnames, key_prefix=""):
	"""
	:param hashes: iterable of tree hash names
	:return: None
	Sub-tree contents should already be processed.

	"""

	if "git-sha1" in hnames:
		git_sha1_data = list()

		for idx_sub, sub in enumerate(node["contents"]):
			name = sub["name"]
			n = name if sys.hexversion < 0x03000000 else name.encode("utf-8")
			h = codecs.decode(sub[key_prefix + "git-sha1"], "hex")
			if sub["type"] == "folder":
				git_sha1_data.append(b"40000 %s\0%s" % (n, h))
			else:
				git_sha1_data.append(b"100644 %s\0%s" % (n, h))

		s = b"".join(git_sha1_data)
		h = hashlib.sha1()
		h.update(("tree %d\0" % len(s)).encode("utf-8"))
		h.update(s)
		hval = h.hexdigest()
		node[key_prefix + "git-sha1"] = hval


class DsDir(object):
	"""
	"""
	def __init__(self, hash_dirs=["git-sha1"], hash_files=["sha1"], logger=None):
		self._hash_dirs = hash_dirs
		self._hash_files = hash_files
		self._root = dict()
		self._log = logger or logging
		self._log.info("Will hash dirs with %s and files with %s", self._hash_dirs, self._hash_files)

	def create_file(self, parent, filename):
		"""
		:param parent: parent path
		"""
		out = dict()
		out["type"] = "file"
		out["name"] = filename
		out["path"] = os.path.join(parent, filename)
		out["size"] = os.path.getsize(out["path"])

		h_file(out, set(list(self._hash_dirs) + list(self._hash_files)))

		return out

	def create_folder(self, path, node):
		"""
		Recursively create a folder...
		"""

		out = dict()
		out["type"] = "folder"
		out["name"] = os.path.basename(path)
		out["path"] = path
		out["contents"] = contents = list()

		for k, v in sorted(node.items()):
			if v is None:
				try:
					res = self.create_file(path, k)
					contents.append(res)
				except OSError as e:
					self._log.warn("File %s couldn't be processed, ignoring", path)
			else:
				path_ = os.path.join(path, k)
				res = self.create_folder(path_, v)
				contents.append(res)

		h_tree(out, self._hash_dirs)
		out["size"] = sum(x["size"] for x in contents)

		return out


	def create(self, top, files, lang="xml"):
		files = rec_files(files)

		for file in files:
			self._log.info("- considering file %s", file)

		root = dict()
		tree_add_paths(files, root)

		for k in path_split(top):
			logging.info("Entering: %s (%s)", k, list(root.keys()))
			root = root[k]

		def pr(d, indent=0):
			for k, v in sorted(d.items()):
				if v is None:
					self._log.info("%s %s", " " * indent, k)
				else:
					self._log.info("%s %s/", " " * indent, k)
					pr(v, indent=indent+1)

		self._log.info("File hierarchy:")
		pr(root)

		tree = self.create_folder(top, root)

		self._log.info("Internal representation: %s", LazyPprintStr(tree))
		return tree


	def validate_file(self, node, hnames=None):
		"""
		:param hnames: inherited hashes to compute
		"""

		self._log.info("Validating %s", node["path"])
		errors = []

		if hnames is None:
			hnames = set([ x for x in all_hash_files if x in node ])
		else:
			hnames = set(hnames).union(set([ x for x in all_hash_files if x in node ]))

		path = node["path"]

		h_file(node, hnames, key_prefix="val-")

		for hname in hnames:
			computed = node["val-%s" % hname]
			expected = node.get(hname, None)
			if expected is not None and computed != expected:
				errors.append("%s: %s check vailure: %s, expected %s" \
				 % (path, hname, computed, expected))

		return errors


	def validate_folder(self, node, hnames=None):
		"""
		:param hnames: inherited hashes to compute
		"""
		errors = list()

		if hnames is None:
			hnames = set([ x for x in all_hash_dirs if x in node ])
		else:
			hnames = set(hnames).union(set([ x for x in all_hash_dirs if x in node ]))

		path = node["path"]

		for idx_ct, ct in enumerate(node["contents"]):
			if ct["type"] == "folder":
				errors += self.validate_folder(ct, hnames)
			else:
				errors += self.validate_file(ct, hnames)

		if hnames:

			self._log.info("Validating %s/", node["path"])

			h_tree(node, hnames, key_prefix="val-")

			for hname in hnames:
				computed = node["val-%s" % hname]
				expected = node[hname]
				if computed != expected:
					errors.append("%s: %s check vailure: %s, expected %s" \
					 % (path, hname, computed, expected))

		return errors

	def validate(self, tree):

		errors = list()

		#self._log.info("Internal representation: %s", LazyPprintStr(tree))

		errors = self.validate_folder(tree)

		return errors

