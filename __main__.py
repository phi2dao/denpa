import argparse
from . import *

parser = argparse.ArgumentParser(prog=__package__)
parser.add_argument('language')
parser.add_argument('lexicon', nargs='?')
group = parser.add_mutually_exclusive_group()
group.add_argument('-s', '--sorted', action='store_true')
group.add_argument('-S', '--sorted-only', action='store_true')
group = parser.add_mutually_exclusive_group()
group.add_argument('-t', '--times', default=1, type=int, metavar='num')
group.add_argument('-T', '--text', nargs='?', const=11, type=int, metavar='num')

args = parser.parse_args()
sorted = args.sorted or args.sorted_only

try:
    lang = Language(args.language)
    if args.lexicon:
        with open(args.lexicon, 'r', encoding='utf-8') as f:
            words = [lang.normalize(line) for line in f]
        if not args.sorted_only:
            words = lang.apply(words)
        if sorted:
            words = lang.sorted(words)
        print(*words, sep='\n')
    elif args.text:
        print(lang.textify(args.text))
    else:
        print(*lang.generate(args.times, sorted=sorted), sep='\n')
except LanguageException as e:
    e.exit()
except FileNotFoundError as e:
    parser.error(f"can't open language or lexicon '{e.filename}': {e}")
