"""Build the 18 reviewed Ravager figures on a stock or previously modified OBJEX."""
import argparse
from pathlib import Path
import tempfile

import people_dress
import sl_figures as s
from restyle import figure_walks, knight_melee


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.resolve() == args.base.resolve():
        parser.error('choose a separate output file to preserve the base')

    pictures = {2424, *figure_walks.PICTURES, *knight_melee.PICTURES}
    with tempfile.TemporaryDirectory() as folder:
        candidate = str(Path(folder) / 'OBJEX.GFF')
        people_dress.build(str(args.base), candidate, people_dress.load_data())
        _, built = s.load(candidate)
        changes = {key: chunk for key, chunk in built.items()
                   if key[1] in pictures and key[0] in ('BMP ', 'CBMP', 'SCMD')}
        s.write_ranged(str(args.base), changes, str(args.output))


if __name__ == '__main__':
    main()
