"""Validate generated layouts without requiring Ubuntu's exact XKB version."""

import csv
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ("to_hid_keyboard", "from_hid_keyboard", "composition")


def resolve_layout(path, chain=()):
    if path in chain:
        raise AssertionError("Parent cycle: " + repr(chain + (path,)))
    data = json.loads((ROOT / path).read_text())
    merged = {section: {} for section in SECTIONS}
    if data.get("parent"):
        merged = resolve_layout(data["parent"], chain + (path,))
    for section in SECTIONS:
        merged[section].update(data.get(section, {}))
    return merged


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (ROOT / "tools/xkb-catalog.tsv").open() as source:
            cls.catalog = list(csv.DictReader(source, delimiter="\t"))
        cls.documents = {str(p.relative_to(ROOT)): json.loads(p.read_text())
                         for p in (ROOT / "keyboards").glob("xkb_*.json")}

    def test_catalog_covers_every_alias_and_file(self):
        catalog_aliases = set()
        referenced = set()
        for entry in self.catalog:
            alias, path = entry["xkb_name"], entry["file"]
            self.assertNotIn(alias, catalog_aliases)
            catalog_aliases.add(alias)
            if not path:
                self.assertEqual(alias, "xkb:custom")
                self.assertEqual(entry["unavailable_positions"], "no installed definition")
                continue
            self.assertIn(path, self.documents)
            self.assertIn(alias, self.documents[path]["name"])
            self.assertEqual(entry["parent"], self.documents[path]["parent"])
            referenced.add(path)
        self.assertEqual(referenced, set(self.documents))
        aliases = {alias for data in self.documents.values() for alias in data["name"]}
        self.assertEqual(aliases, {row["xkb_name"] for row in self.catalog if row["file"]})

    def test_global_aliases_do_not_conflict(self):
        seen = {}
        for folder in ("base", "keyboards"):
            for path in (ROOT / folder).glob("*.json"):
                for alias in json.loads(path.read_text())["name"]:
                    alias = alias.casefold()
                    self.assertTrue(alias not in seen or seen[alias] == path,
                                    "Conflicting alias: " + alias)
                    seen[alias] = path

    def test_all_compositions_resolve_to_usb_keys(self):
        for path, data in self.documents.items():
            with self.subTest(layout=path):
                merged = resolve_layout(path)
                aliases = {name.casefold(): int(code, 16)
                           for name, code in merged["from_hid_keyboard"].items()}
                for output, sequence in merged["composition"].items():
                    if sequence is None:
                        continue
                    self.assertTrue(output and output.isprintable())
                    self.assertTrue(sequence)
                    for combo in sequence:
                        self.assertTrue(combo)
                        usages = [aliases[key.casefold()] for key in combo]
                        self.assertEqual(len(usages), len(set(usages)))
                        self.assertTrue(all(0 < usage <= 0xFF for usage in usages))
                active = sum(value is not None for value in merged["composition"].values())
                rows = [row for row in self.catalog if row["file"] == path]
                self.assertTrue(all(int(row["compositions"]) == active for row in rows))
                self.assertIn(data["hid_locale"], json.loads((ROOT / "base/base.json").read_text())["from_hid_locale"])

    def test_arrangement_parents_and_international_text(self):
        self.assertEqual(self.documents["keyboards/xkb_be.json"]["parent"], "base/azerty-keys.json")
        self.assertEqual(self.documents["keyboards/xkb_de.json"]["parent"], "base/qwertz-keys.json")
        self.assertEqual(self.documents["keyboards/xkb_us.json"]["parent"], "base/qwerty-keys.json")
        for path, characters in (("keyboards/xkb_be.json", "é€ê¨"),
                                 ("keyboards/xkb_ru.json", "йЯ"),
                                 ("keyboards/xkb_gr.json", "αΩ"),
                                 ("keyboards/xkb_il.json", "שת")):
            compositions = resolve_layout(path)["composition"]
            self.assertTrue(all(compositions.get(char) for char in characters), path)
        # US punctuation must not leak into a non-Latin layout through inheritance.
        self.assertIsNone(resolve_layout("keyboards/xkb_ru.json")["composition"].get("q"))

    def test_layouts_package_can_load_and_compose(self):
        try:
            import layouts
        except ImportError:
            self.skipTest("The optional layouts package is not installed")
        manager = layouts.Layouts(layout_path=str(ROOT))
        for path, data in self.documents.items():
            with self.subTest(layout=path):
                layout = manager.get_layout(data["name"][0])
                aliases = layout.dict("from_hid_keyboard", key_caps=True)
                for output in layout.json()["composition"]:
                    if len(output) != 1:
                        continue  # The package's compose() API accepts individual characters.
                    for combo in layout.compose(output, no_clears=True):
                        self.assertTrue(all(key.upper() in aliases for key in combo))


if __name__ == "__main__":
    unittest.main()
