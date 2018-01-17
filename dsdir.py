#!/usr/bin/env python
# -*- coding: utf-8 vi:noet
# dsdir management

import sys, io, os, re, hashlib, collections, codecs

import lxml.etree

ns = "dsdir"
ns = None

namespaces = {
 ns: "http://zougloub.github.io/dsdir/v1",
}

NS = namespaces[ns]

HASH = "hash" # "{%s}hash" % NS
NAME = "name" # "{%s}name" % NS

# TODO os.path -> /

def dsdir_create_file(parent, filename):
	path = os.path.join(parent, filename)

	htype = "sha1"
	h = getattr(hashlib, htype)()

	htype = "git-sha1"
	h.update(("blob %d" % os.path.getsize(path)).encode() + b"\0")

	with io.open(path, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			h.update(chunk)
		hval = h.hexdigest()

	elt = lxml.etree.Element("{%s}file" % NS, nsmap=namespaces)
	elt.attrib[HASH] =  "%s:%s" % (htype, hval)
	elt.attrib[NAME] = filename
	return elt


def tree_add_paths(paths, tree):
	for path in paths:
		parts = path.split("/", 1)
		if len(parts) == 1: # leaf
			tree[parts[0]] = None
		else:
			node, sub = parts
			if node not in tree:
				tree[node] = dict()
			tree_add_paths([sub], tree[node])

def rec_files(files_sel):
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

def dsdir_create_folder(path, root):
	"""
	"""
	elt = lxml.etree.Element("{%s}folder" % NS, nsmap=namespaces)

	ret = list()
	for k, v in sorted(root.items()):
		if v is None:
			res = dsdir_create_file(path, k)
			elt.append(res)
			h = codecs.decode(res.attrib[HASH].split(":")[1], "hex")
			n = res.attrib[NAME].encode("utf-8")
			ret.append(b"100644 %s\0%s" % (n, h))
		else:
			path_ = os.path.join(path, k)
			res = dsdir_create_folder(path_, v)
			elt.append(res)
			h = codecs.decode(res.attrib[HASH].split(":")[1], "hex")
			n = res.attrib[NAME].encode("utf-8")
			ret.append(b"040000 %s\0%s" % (n, h))

	s = b"".join(ret)

	htype = "sha1"
	h = getattr(hashlib, htype)()
	htype = "git-sha1"
	h.update(("tree %d\0" % len(s)).encode("utf-8"))
	h.update(s)
	hval = h.hexdigest()
	elt.attrib[HASH] =  "%s:%s" % (htype, hval)
	elt.attrib[NAME] = os.path.basename(path)
	return elt


def dsdir_create(files):
	files = rec_files(files)

	#for file in files:
	#	print(file)

	root = dict()
	tree_add_paths(files, root)

	def pr(d, indent=0):
		for k, v in sorted(d.items()):
			if v is None:
				print("%s %s" % (" " * indent, k))
			else:
				print("%s %s/" % (" " * indent, k))
				pr(v, indent=indent+1)

	#pr(root)

	res = dsdir_create_folder("", root)
	res.tag = "{%s}contents" % NS
	del res.attrib["name"]

	elt = lxml.etree.Element("{%s}dataset" % NS, nsmap=namespaces)
	elt.append(res)


	#lxml.etree.cleanup_namespaces(res)

	print(lxml.etree.tostring(elt,
	 pretty_print=True,
	 xml_declaration=True,
	))


def full_path(x):
	res = [x.attrib[NAME]]
	while True:
		try:
			pname = x.getparent().attrib[NAME]
		except KeyError:
			break

		res.insert(0, pname)
		x = x.getparent()

	return os.path.join(*res)


def dsdir_validate_file(element):
	path = full_path(element)

	try:
		hashval = element.attrib[HASH]
	except KeyError:
		return None

	hashes = hashval.split(" ")

	ret = list()

	for hval in hashes:
		m = re.match(r"(?P<type>\S+):(?P<value>\S+)", hval)
		if m is None:
			raise ValueError(hval)

		htype = m.group("type")
		hval = m.group("value")

		h = getattr(hashlib, htype)()
		with io.open(path, "rb") as f:
			for chunk in iter(lambda: f.read(4096), b""):
				h.update(chunk)
		hval2 = h.hexdigest()
		if hval != hval2:
			raise RuntimeError("Invalid checksum for %s: %s expected %s" % (path, hval2, hval))


def dsdir_validate_folder(folder):
	ret = list()
	elements = folder.xpath("dsdir:*", namespaces=namespaces)
	for idx_elt, elt in enumerate(elements):
		if elt.tag == "{%s}file" % NS:
			res = dsdir_validate_file(elt)
		elif elt.tag == "{%s}folder" % NS:
			res = dsdir_validate_folder(elt)

	try:
		name = folder.attrib[NAME]
	except KeyError:
		name = "."

	try:
		hashval = folder.attrib[HASH]
	except KeyError:
		return

	ret = "%s %s" % (hashval, name)

	return ret

def dsdir_validate(f):

	raise NotImplementedError()

	schema_file = os.path.join(os.path.dirname(__file__), "schema-v1.xsd")
	with io.open(schema_file, "rb") as f_s:
		xmlschema_doc = lxml.etree.parse(f_s)
	xmlschema = lxml.etree.XMLSchema(xmlschema_doc)

	doc = lxml.etree.parse(f)
	res = xmlschema.validate(doc)
	if not res:
		raise RuntimeError("Invalid XML")
		# TODO details


	global ns
	if ns != "dsdir":
		NS = namespaces["dsdir"] = namespaces[ns]
		del namespaces[ns]
		ns = "dsdir"

	contents = doc.xpath("//%s:contents" % ns, namespaces=namespaces)[0]

	dsdir_validate_folder(contents)


if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(
	 description="dsdir processor",
	)

	subparsers = parser.add_subparsers(
	 help='the command; type "%s COMMAND -h" for command-specific help' % sys.argv[0],
	 dest='command',
	)

	subp = subparsers.add_parser(
	 "create",
	 help="create a dsdir",
	)

	subp.add_argument("files",
	 nargs="*",
	)

	subp = subparsers.add_parser(
	 "validate",
	 help="validate a dsdir",
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

	if args.command == "create":
		dsdir_create(args.files)
	elif args.command == "validate":
		if args.filename is None:
			f = sys.stdin.buffer
		else:
			f = io.open(args.filename, "rb")
		dsdir_validate(f)
