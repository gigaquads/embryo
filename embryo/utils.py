from .constants import PROMPT_STYLES


def say(fstr, **format_vars):
    print(PROMPT_STYLES['say'] + ' ' + fstr.format(**format_vars))


def scream(fstr, **format_vars):
    print(PROMPT_STYLES['scream'] + ' ' + fstr.format(**format_vars))
