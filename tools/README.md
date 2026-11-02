# Importing Ubuntu's keyboard layouts

`import_xkb.py` imports every distinct layout/variant registered in the installed
`evdev.xml` and `evdev.extras.xml` catalogs. It compiles each entry using
libxkbcommon with the `evdev` rules, `pc105` model, and no additional options.
Personal XKB configuration and personal Compose tables are excluded.

The checked-in snapshot comes from Ubuntu's `xkb-data` package. The exact version,
Compose checksum, and import totals are in [xkb-source.txt](xkb-source.txt).
[xkb-catalog.tsv](xkb-catalog.tsv) lists every registered entry, its description,
output file, parent, composition count, and any unavailable key positions.
The `custom` catalog entry is a placeholder without an installed definition;
it is recorded in the catalog rather than assigned a fabricated layout.

Select a layout by its unique alias, for example:

* `xkb:gb`: default British layout.
* `xkb:us(dvorak)`: US Dvorak variant.
* `xkb:be(nodeadkeys)`: Belgian variant without dead keys.

Generated filenames retain XKB identifiers because a country or language can
have many layouts and variants; these are not one-to-one with glibc locales.
Exact duplicates with the same USB HID locale share a file and retain all aliases,
countries, and source descriptions. Existing manually maintained files and their
aliases remain unchanged. A USB HID locale is `Undefined` when there is no
matching descriptor in the repository's USB HID locale table.

## Regenerate and verify

Use Python 3.8+, libxkbcommon 1.6+, and the Ubuntu `xkb-data` and `libx11-data`
packages. The importer uses Python's standard library and ctypes; it needs no
Python packages or network access.

```sh
python3 tools/import_xkb.py
python3 tools/import_xkb.py --check
python3 -m unittest discover -s tests -p 'test_*.py'
```

`--check` regenerates every entry in memory, replays its compositions, and
compares the results with the checked-in files without changing them. A different
XKB or Compose version can legitimately produce a different snapshot. The
importer overwrites only files bearing its generated-file marker and removes
obsolete generated keyboard files. To change a generated definition, update
the source or importer and regenerate it.

The tests check catalog coverage, alias uniqueness, parent chains, USB key
references, composition counts, and representative international characters.
If the optional `layouts` Python package is installed, they also load every
generated file through that package and exercise its per-character compose API.
The repository's original `tests/python-test.py` remains a discovery check.

## Inheritance and key names

The importer generates composition-free `base/azerty-keys.json`,
`base/qwertz-keys.json`, and `base/qwerty-keys.json` from the corresponding
existing bases. These share the physical mappings without inheriting characters
that the target layout cannot type. This also avoids `null` composition removals,
which the `layouts` 0.4.10 loader rejects despite their documented use.
Variants inherit their country default when the arrangement matches and doing
so would not introduce unsupported characters.

`XKB_AD01`, `XKB_AC01`, and similar aliases identify physical keys and resolve to
USB HID usages. Composition sequences use these stable names so remapping a
letter or modifier cannot change another character's physical sequence. Display
names reflect each layout's unmodified symbols. The backslash position uses ISO
usage `0x32`; ANSI usage `0x31` is given the same display name.

## Character coverage

The importer discovers combinations using the layout's actual momentary Shift,
third-level, fifth-level, and group selectors, including selectors moved to
Caps Lock or other keys. It derives dead-key sequences from the installed system
UTF-8 Compose table. Every emitted sequence is replayed as physical key presses
through the compiled XKB keymap and Compose state machine, including inherited
compositions. The chosen sequence minimizes key events and held modifiers.

This is a keyboard mapping collection, not an input method engine. Persistent
group switches, lock/latch states, IME conversion (such as Hangul or Kanji), and
arbitrary XKB options are not synthesized. Unreachable printable/dead-key
positions are listed as `KEY:groupN:levelN` in the catalog; `unmapped:` marks a
position without a supported physical USB mapping. Conventional NumLock keypad
layers and unchanged generic evdev multimedia/calculator extensions are excluded
from that warning list. A definition can therefore be
imported while some of its optional groups or levels remain unavailable for
text composition. The catalog makes those limits explicit.

Some XKB events and Compose sequences produce multiple characters. Their whole
output string is retained as the composition key, as permitted by this JSON
format. The `layouts` package's current `compose()` API consumes individual
characters and cannot request such a string as one atomic event. Typing with a
different operating system's layout or Compose table may produce different text.

The source package notices are retained in
[xkb-data-copyright.txt](xkb-data-copyright.txt) and
[libx11-data-copyright.txt](libx11-data-copyright.txt).
