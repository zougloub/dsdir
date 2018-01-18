#!/usr/bin/env python
# -*- coding: utf-8 vi:noet
# dsdir management

import sys, io, os, re, hashlib, collections, codecs, logging, json

import lxml.etree

ns = "dsdir"
ns = None

namespaces = {
 ns: "http://zougloub.github.io/dsdir/v1",
}

NS = namespaces[ns]

HASH = "hash" # "{%s}hash" % NS
NAME = "name" # "{%s}name" % NS

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


def tree_add_paths(paths, tree, sep=os.path.sep):
	"""
	Transform a series of (top-down) paths into a hierarchy.
	:param paths: iterable of slash-separated strings
	:param tree: dictionary representing a tree. Leaves have None value.
	"""
	for path in paths:
		parts = path.split(sep, 1)
		if len(parts) == 1: # leaf
			tree[parts[0]] = None
		else:
			node, sub = parts
			if node not in tree:
				tree[node] = dict()
			tree_add_paths([sub], tree[node])

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

def full_path(x):
	try:
		res = [x.attrib[NAME]]
	except KeyError:
		return ""

	while True:
		try:
			pname = x.getparent().attrib[NAME]
		except KeyError:
			break

		res.insert(0, pname)
		x = x.getparent()

	return os.path.join(*res)


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

class Creator(object):
	"""
	"""
	def __init__(self, hash_dirs=["git-sha1"], hash_files=["sha1"], logger=None):
		self._hash_dirs = hash_dirs
		self._hash_files = hash_files
		self._root = dict()
		self._log = logger or logging
		self._log.info("Will hash dirs with %s and files with %s", self._hash_dirs, self._hash_files)

	def create_file(self, parent, filename):
		out = dict()
		out["type"] = "file"
		out["name"] = filename
		out["path"] = os.path.join(parent, filename)

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
				res = self.create_file(path, k)
				contents.append(res)
			else:
				path_ = os.path.join(path, k)
				res = self.create_folder(path_, v)
				contents.append(res)

		h_tree(out, self._hash_dirs)

		return out

	def to_xml(self, tree, is_root=True):

		if is_root:
			elt = lxml.etree.Element("{%s}contents" % (NS), nsmap=namespaces)
		else:
			elt = lxml.etree.Element("{%s}folder" % (NS), nsmap=namespaces)

		for idx_content, content in enumerate(tree.get("contents", [])):

			if content["type"] == "folder":
				sub = self.to_xml(content, is_root=False)
				elt.append(sub)
			else:
				sub = lxml.etree.Element("{%s}file" % NS, nsmap=namespaces)
				for aname in ("size",):
					aval = content.get(aname, None)
					if aval is not None:
						sub.attrib[aname] = aval

				hashes = []
				for htype in set(list(self._hash_files)):
					hval = content[htype]
					hashes.append("%s:%s" % (htype, hval))

				if hashes:
					sub.attrib["hash"] = " ".join(hashes)

				name = content["name"]
				n = name.decode("utf-8") if sys.hexversion < 0x03000000 else name
				sub.attrib["name"] = n
				elt.append(sub)

		hashes = []
		for htype in self._hash_dirs:
			hval = tree[htype]
			hashes.append("%s:%s" % (htype, hval))
			if hashes:
				elt.attrib["hash"] = " ".join(hashes)

		if not is_root:
			elt.attrib["name"] = tree["name"]

		return elt

	def create(self, files):
		files = rec_files(files)

		for file in files:
			self._log.info("- considering file %s", file)

		root = dict()
		tree_add_paths(files, root)

		def pr(d, indent=0):
			for k, v in sorted(d.items()):
				if v is None:
					self._log.info("%s %s", " " * indent, k)
				else:
					self._log.info("%s %s/", " " * indent, k)
					pr(v, indent=indent+1)

		self._log.info("File hierarchy:")
		pr(root)

		tree = self.create_folder("", root)

		self._log.info("Internal representation: %s", LazyPprintStr(tree))

		xml = self.to_xml(tree)

		elt = lxml.etree.Element("{%s}dataset" % NS, nsmap=namespaces)
		elt.append(xml)

		return elt

class Validator(object):
	def __init__(self, logger=None):
		self._log = logger or logging

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

	def validate(self, f, validate_schema=True):

		errors = list()

		doc = lxml.etree.parse(f)

		if validate_schema:
			schema_file = os.path.join(os.path.dirname(__file__), "schema-v1.xsd")
			with io.open(schema_file, "rb") as f_s:
				xmlschema_doc = lxml.etree.parse(f_s)
			xmlschema = lxml.etree.XMLSchema(xmlschema_doc)

			res = xmlschema.validate(doc)
			if not res:
				self._log.error("Invalid XML")
				for x in xmlschema.error_log:
					self._log.error(x)

			if errors:
				return errors

		global ns
		if ns != "dsdir":
			NS = namespaces["dsdir"] = namespaces[ns]
			del namespaces[ns]
			ns = "dsdir"

		contents = doc.xpath("//%s:contents" % ns, namespaces=namespaces)[0]

		tree = self.from_xml(contents)

		self._log.info("Internal representation: %s", LazyPprintStr(tree))

		errors = self.validate_folder(tree)

		return errors

	def from_xml(self, elem):

		out = dict()

		try:
			out["name"] = elem.attrib[NAME]
		except KeyError:
			out["name"] = ""

		out["path"] = full_path(elem)

		if elem.tag in ("{%s}folder" % NS, "{%s}contents" % NS):
			out["type"] = "folder"
			try:
				hashes = elem.attrib["hash"].split(" ")
				for hval in hashes:
					m = re.match(r"(?P<type>\S+):(?P<value>\S+)", hval)

					assert m is not None

					htype = m.group("type")
					hval = m.group("value")
					out[htype] = hval
			except KeyError:
				pass
			out["contents"] = [ self.from_xml(x) for x in elem ]
		else:
			out["type"] = "file"
			try:
				hashes = elem.attrib["hash"].split(" ")
				for hval in hashes:
					m = re.match(r"(?P<type>\S+):(?P<value>\S+)", hval)

					assert m is not None

					htype = m.group("type")
					hval = m.group("value")
					out[htype] = hval
			except KeyError:
				pass

		return out

if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(
	 description="dsdir processor",
	)

	parser.add_argument(
	 "--verbose",
	 type=int,
	 default=0,
	)

	subparsers = parser.add_subparsers(
	 help='the command; type "%s COMMAND -h" for command-specific help' % sys.argv[0],
	 dest='command',
	)

	subp = subparsers.add_parser(
	 "create",
	 help="create a dsdir",
	)

	subp.add_argument(
	 "--exclude",
	 action="append",
	 default=list(),
	)

	def csl(x):
		if x == "":
			return []
		return x.split(",")

	subp.add_argument(
	 "--hash-files",
	 type=csl,
	 default=["sha1"],
	)

	subp.add_argument(
	 "--hash-trees",
	 type=csl,
	 default=["git-sha1"],
	)

	subp.add_argument(
	 "--output",
	 type=argparse.FileType('wb'),
	 default=sys.stdout.buffer if sys.hexversion >= 0x03000000 else sys.stdout,
	)


	subp.add_argument("files",
	 nargs="+",
	)

	subp = subparsers.add_parser(
	 "validate",
	 help="validate a dsdir",
	)

	subp.add_argument(
	 "--validate-schema",
	 action="store_true",
	)

	subp.add_argument("filename",
	 nargs="?",
	)


	try:
		import argcomplete
		argcomplete.autocomplete(parser)
	except:
		pass

	args = parser.parse_args()

	if args.verbose > 0:
		logging.basicConfig(level=logging.INFO)

	if args.command == "create":
		creator = Creator(hash_files=args.hash_files, hash_dirs=args.hash_trees)
		files = set()
		exclusions = set(args.exclude)

		if args.output != parser.get_default("output"):
			exclusions.add(args.output.name)

		for path in args.files:
			if path in exclusions:
				continue
			if path == ".":
				for path in os.listdir("."):
					if path in (".", ".."):
						continue
					if path in exclusions:
						continue
					files.add(path)
				continue
			files.add(path)
		root = creator.create(files)

		b = lxml.etree.tostring(root,
		 encoding="utf-8",
		 pretty_print=True,
		 xml_declaration=True,
		)

		f = args.output
		f.write(b)
		f.flush()

	elif args.command == "validate":
		if args.filename is None:
			f = sys.stdin.buffer
		else:
			f = io.open(args.filename, "rb")
		validator = Validator()
		errors = validator.validate(f, validate_schema=args.validate_schema)
		if errors:
			sys.stderr.write("Verification errors:\n")
			for error in errors:
				sys.stderr.write("- %s\n" % error)
			raise SystemExit(1)
