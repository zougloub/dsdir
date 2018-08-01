#!/usr/bin/env python
# -*- coding: utf-8 vi:noet
# dsdir xml io

import sys, re, os

import lxml.etree

from .. import LazyPprintStr

ns = "dsdir"
ns = None

namespaces = {
 ns: "http://zougloub.github.io/dsdir/v1",
}

NS = namespaces[ns]

HASH = "hash" # "{%s}hash" % NS
NAME = "name" # "{%s}name" % NS


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

def to_lxml(dsdir, tree, is_root=False):

	if is_root:
		elt = lxml.etree.Element("{%s}contents" % (NS), nsmap=namespaces)
	else:
		elt = lxml.etree.Element("{%s}folder" % (NS), nsmap=namespaces)

	for idx_content, content in enumerate(tree.get("contents", [])):

		if content["type"] == "folder":
			sub = to_lxml(dsdir, content)
			elt.append(sub)
		else:
			sub = lxml.etree.Element("{%s}file" % NS, nsmap=namespaces)
			for aname in ("size",):
				aval = content.get(aname, None)
				if aval is not None:
					sub.attrib[aname] = str(aval)

			hashes = []
			for htype in set(list(dsdir._hash_files)):
				hval = content[htype]
				hashes.append("%s:%s" % (htype, hval))

			if hashes:
				sub.attrib["hash"] = " ".join(hashes)

			name = content["name"]
			n = name.decode("utf-8") if sys.hexversion < 0x03000000 else name
			sub.attrib["name"] = n
			elt.append(sub)

	hashes = []
	for htype in dsdir._hash_dirs:
		hval = tree[htype]
		hashes.append("%s:%s" % (htype, hval))
		if hashes:
			elt.attrib["hash"] = " ".join(hashes)

	if not is_root:
		elt.attrib["name"] = tree["name"]
	else:
		root = lxml.etree.Element("{%s}dataset" % NS, nsmap=namespaces)
		root.append(elt)
		elt = root

	return elt


def to_xml(dsdir, tree):
	xroot = to_lxml(dsdir, tree, is_root=True)

	return lxml.etree.tostring(xroot,
	 encoding="utf-8",
	 pretty_print=True,
	 xml_declaration=True,
	)


def validate_xml(dsdir, f, validate_schema=True):

	errors = list()

	doc = lxml.etree.parse(f)

	if validate_schema:
		schema_file = os.path.join(os.path.dirname(__file__), "schema-v1.xsd")
		with io.open(schema_file, "rb") as f_s:
			xmlschema_doc = lxml.etree.parse(f_s)
		xmlschema = lxml.etree.XMLSchema(xmlschema_doc)

		res = xmlschema.validate(doc)
		if not res:
			validator._log.error("Invalid XML")
			for x in xmlschema.error_log:
				validator._log.error(x)

		if errors:
			return errors

	global ns
	if ns != "dsdir":
		NS = namespaces["dsdir"] = namespaces[ns]
		del namespaces[ns]
		ns = "dsdir"

	contents = doc.xpath("//%s:contents" % ns, namespaces=namespaces)[0]

	tree = from_xml(dsdir, contents)

	dsdir._log.info("Internal representation: %s", LazyPprintStr(tree))

	errors = dsdir.validate_folder(tree)

	return errors


def from_xml(dsdir, elem):

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
		out["contents"] = [ from_xml(dsdir, x) for x in elem ]
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
