import argparse
from . import *

parser = argparse.ArgumentParser(prog=f'python -m {__package__}')
parser.add_argument('language')
parser.add_argument('lexicon', nargs='?')
parser.add_argument('-s', '--sorted', action='store_true')
group = parser.add_mutually_exclusive_group()
group.add_argument('-t', '--times', default=1, type=int, metavar='num')
group.add_argument('--text', nargs='?', const=11, type=int, metavar='num')
args = parser.parse_args()

try:
    lang = Language().open(args.language)
    if args.lexicon:
        words = [lang.normalizew(line) for line in Segment.open(args.lexicon)]
    elif args.text:
        print(lang.textify(args.text))
    else:
        for word in lang.generate(args.times, sorted=args.sorted):
            print(word)
except DenpaError as e:
    e.exit()
except FileNotFoundError as e:
    DenpaError(f'no file or directory "{e.filename}"').exit()
