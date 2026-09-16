"""This tool allows generation of gettext .mo compiled files, pot files from source code files
and pot files for merging.

Three new builders are added into the constructed environment:

- gettextMoFile: generates .mo file from .pot file using msgfmt.
- gettextPotFile: Generates .pot file from source code files.
- gettextMergePotFile: Creates a .pot file appropriate for merging into existing .po files.

To properly configure get text, define the following variables:

- gettext_package_bugs_address
- gettext_package_name
- gettext_package_version


"""

import shutil

import ast
from pathlib import Path

from SCons.Action import Action


def _compile_mo_with_polib(target, source, env):
	import polib

	polib.pofile(str(source[0])).save_as_mofile(str(target[0]))
	return 0


def _generate_pot_with_polib(target, source, env, *, omit_header=False, include_locations=True):
	import polib

	entries = {}
	for source_node in source:
		path = Path(str(source_node))
		if path.suffix.casefold() != ".py":
			continue
		tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
		for node in ast.walk(tree):
			if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
				continue
			name = node.func.id
			context = None
			msgid = None
			plural = None
			if name == "_" and node.args:
				msgid = node.args[0]
			elif name == "pgettext" and len(node.args) >= 2:
				context, msgid = node.args[:2]
			elif name == "ngettext" and len(node.args) >= 2:
				msgid, plural = node.args[:2]
			elif name == "npgettext" and len(node.args) >= 3:
				context, msgid, plural = node.args[:3]
			if not isinstance(msgid, ast.Constant) or not isinstance(msgid.value, str):
				continue
			if context is not None and (
				not isinstance(context, ast.Constant) or not isinstance(context.value, str)
			):
				continue
			if plural is not None and (
				not isinstance(plural, ast.Constant) or not isinstance(plural.value, str)
			):
				continue
			key = (context.value if context else None, msgid.value, plural.value if plural else None)
			entries.setdefault(key, []).append((path.as_posix(), node.lineno))

	pot = polib.POFile()
	if not omit_header:
		pot.metadata = {
			"Project-Id-Version": str(env.get("gettext_package_version", "")),
			"Report-Msgid-Bugs-To": str(env.get("gettext_package_bugs_address", "")),
			"Content-Type": "text/plain; charset=UTF-8",
			"Content-Transfer-Encoding": "8bit",
			"MIME-Version": "1.0",
		}
	for (context, msgid, plural), occurrences in sorted(
		entries.items(),
		key=lambda item: item[0][1].casefold(),
	):
		pot.append(
			polib.POEntry(
				msgctxt=context,
				msgid=msgid,
				msgid_plural=plural or "",
				occurrences=occurrences if include_locations else [],
			),
		)
	pot.save(str(target[0]))
	return 0


def _generate_merge_pot_with_polib(target, source, env):
	return _generate_pot_with_polib(target, source, env, omit_header=True, include_locations=False)


def exists(env):
	return True


XGETTEXT_COMMON_ARGS = (
	"--msgid-bugs-address='$gettext_package_bugs_address' "
	"--package-name='$gettext_package_name' "
	"--package-version='$gettext_package_version' "
	"--keyword=pgettext:1c,2 "
	"-c -o $TARGET $SOURCES"
)


def generate(env):
	env.SetDefault(gettext_package_bugs_address="example@example.com")
	env.SetDefault(gettext_package_name="")
	env.SetDefault(gettext_package_version="")

	msgfmt_action = (
		Action("msgfmt -o $TARGET $SOURCE", "Compiling translation $SOURCE")
		if shutil.which("msgfmt")
		else Action(_compile_mo_with_polib, "Compiling translation $SOURCE with polib")
	)
	env["BUILDERS"]["gettextMoFile"] = env.Builder(
		action=msgfmt_action,
		suffix=".mo",
		src_suffix=".po",
	)
	xgettext_action = (
		Action("xgettext " + XGETTEXT_COMMON_ARGS, "Generating pot file $TARGET")
		if shutil.which("xgettext")
		else Action(_generate_pot_with_polib, "Generating pot file $TARGET with polib")
	)

	env["BUILDERS"]["gettextPotFile"] = env.Builder(
		action=xgettext_action,
		suffix=".pot",
	)
	merge_action = (
		Action(
			"xgettext " + "--omit-header --no-location " + XGETTEXT_COMMON_ARGS,
			"Generating pot file $TARGET",
		)
		if shutil.which("xgettext")
		else Action(_generate_merge_pot_with_polib, "Generating pot file $TARGET with polib")
	)

	env["BUILDERS"]["gettextMergePotFile"] = env.Builder(
		action=merge_action,
		suffix=".pot",
	)
