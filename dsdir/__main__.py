#!/usr/bin/env python
# -*- coding: utf-8 vi:noet
# dsdir command-line entry point

import sys, io, os, logging

from . import DsDir, common_prefix


if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(
	 description="dsdir processor",
	 prog="dsdir",
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

	parser.add_argument(
	 "--format",
	 choices=("xml", "yaml"),
	 default="xml",
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
	 default=["git-sha1", "sha1"],
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


	subp.add_argument("paths",
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
		dsdir = DsDir(hash_files=args.hash_files, hash_dirs=args.hash_trees)
		files = set()
		exclusions = set(args.exclude)

		if args.output != parser.get_default("output"):
			exclusions.add(args.output.name)

		paths = [ os.path.abspath(path) for path in args.paths ]

		if len(paths) > 1:
			# consider top to be what's in common
			top = common_prefix(paths)
		else:
			top = os.path.dirname(paths[0])

		root = dsdir.create(top, paths)

		if args.format == "xml":
			from . import xml as dsdir_xml
			b = dsdir_xml.to_xml(dsdir, root)
		elif args.format == "yaml":
			from . import yaml as dsdir_yaml
			b = dsdir_yaml.to_yaml(dsdir, root)
		else:
			raise NotImplementedError()

		f = args.output
		f.write(b)
		f.flush()

	elif args.command == "validate":
		if args.filename is None:
			f = sys.stdin.buffer
		else:
			f = io.open(args.filename, "rb")
		dsdir = DsDir()

		if args.format == "xml":
			from . import xml as dsdir_xml
			errors = dsdir_xml.validate_xml(dsdir, f, validate_schema=args.validate_schema)
		elif args.format == "yaml":
			from . import yaml as dsdir_yaml
			errors = dsdir_yaml.validate_yaml(dsdir, f)
		else:
			raise NotImplementedError()

		if errors:
			sys.stderr.write("Verification errors:\n")
			for error in errors:
				sys.stderr.write("- %s\n" % error)
			raise SystemExit(1)
