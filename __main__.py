import argparse
from . import *

parser = argparse.ArgumentParser(prog=f'python -m {__package__}')
parser.add_argument('language')
parser.add_argument('lexicon', nargs='?')
group = parser.add_mutually_exclusive_group()
group.add_argument('-s', '--sorted', action='store_true')
group.add_argument('-S', '--sorted-only', action='store_true')
group = parser.add_mutually_exclusive_group()
group.add_argument('-t', '--times', default=1, type=int, metavar='num')
group.add_argument('--text', nargs='?', const=11, type=int, metavar='num')

args = parser.parse_args()
args.sorted = args.sorted or args.sorted_only

try:
    lang = Language().open(args.language)
    if args.lexicon:
        words = map(lang.normalizew, Segment.open(args.lexicon))
        if not args.sorted_only:
            words = lang.apply(words)
        if args.sorted:
            words = lang.sort(words)
        for word in words:
            print(word)
    elif args.text:
        print(lang.textify(args.text))
    else:
        for word in lang.generate(args.times, sorted=args.sorted):
            print(word)
except DenpaError as e:
    e.exit()
except FileNotFoundError as e:
    DenpaError(f'no file or directory "{e.filename}"').exit()
