#! /usr/bin/env python

# run with python generate-domains-blacklist.py -o /opt/homebrew/etc/blocked-names.txt

import os
import re
import sys
from typing import Any, Dict, Iterable, Set, Tuple

import urllib.request as urllib


def parse_time_restricted_list(content: str) -> Tuple[Set[str], Dict[str, str]]:
    rx_comment = re.compile(r'^(#|$)')
    rx_inline_comment = re.compile(r'\s*#\s*[a-z0-9-].*$')
    rx_trusted = re.compile(r'^([*a-z0-9.-]+)\s*(@\S+)?$')

    names = set()
    time_restrictions = {}
    rx_set = [rx_trusted]
    for line in content.splitlines():
        line = str.lower(str.strip(line))
        if rx_comment.match(line):
            continue
        line = rx_inline_comment.sub('', line)
        for rx in rx_set:
            matches = rx.match(line)
            if not matches:
                continue
            name = matches.group(1)
            names.add(name)
            time_restriction = matches.group(2)
            if time_restriction:
                time_restrictions[name] = time_restriction
    return names, time_restrictions


def parse_trusted_list(content: str) -> Tuple[Set[str], Dict[str, str]]:
    names, _time_restrictions = parse_time_restricted_list(content)
    return names, {}


def parse_list(content: str, trusted: bool = False) -> Tuple[Set[str], Dict[str, str]]:
    rx_comment = re.compile(r'^(#|$)')
    rx_inline_comment = re.compile(r'\s*#\s*[a-z0-9-].*$')
    rx_u = re.compile(r'^@*\|\|([a-z0-9.-]+[.][a-z]{2,})\^?(\$(popup|third-party))?$')
    rx_l = re.compile(r'^([a-z0-9.-]+[.][a-z]{2,})$')
    rx_h = re.compile(
        r'^[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}\s+([a-z0-9.-]+[.][a-z]{2,})$'
    )
    rx_mdl = re.compile(r'^"[^"]+","([a-z0-9.-]+[.][a-z]{2,})",')
    rx_b = re.compile(r'^([a-z0-9.-]+[.][a-z]{2,}),.+,[0-9: /-]+,')
    rx_dq = re.compile(r'^address=/([a-z0-9.-]+[.][a-z]{2,})/.')

    if trusted:
        return parse_trusted_list(content)

    names: Set[str] = set()
    time_restrictions: Dict[str, str] = {}
    rx_set = [rx_u, rx_l, rx_h, rx_mdl, rx_b, rx_dq]
    for line in content.splitlines():
        line = str.lower(str.strip(line))
        if rx_comment.match(line):
            continue
        line = rx_inline_comment.sub('', line)
        for rx in rx_set:
            matches = rx.match(line)
            if not matches:
                continue
            name = matches.group(1)
            names.add(name)
    return names, time_restrictions


def print_restricted_name(name: str, time_restrictions: Dict[str, str]) -> None:
    if name in time_restrictions:
        print('{}\t{}'.format(name, time_restrictions[name]))
    else:
        print(
            '# ignored: [{}] was in the time-restricted list, '
            'but without a time restriction label'.format(name)
        )


def load_from_url(url: str) -> Tuple[str, bool]:
    sys.stderr.write('Loading data from [{}]\n'.format(url))
    req = urllib.Request(url=url, headers={'User-Agent': 'dnscrypt-proxy'})
    trusted = False
    req_type = req.type
    if req_type == 'file':
        trusted = True

    response = None
    try:
        response = urllib.urlopen(req, timeout=int(args.timeout))
    except urllib.URLError as err:  # type: ignore
        raise Exception('[{}] could not be loaded: {}\n'.format(url, err))
    if not trusted and response.getcode() != 200:
        raise Exception('[{}] returned HTTP code {}\n'.format(url, response.getcode()))
    content = response.read()
    content = content.decode('utf-8', errors='replace')

    return content, trusted


def name_cmp(name: str) -> str:
    parts = name.split('.')
    parts.reverse()
    return str.join('.', parts)


def has_suffix(names: Iterable[str], name: str) -> bool:
    parts = str.split(name, '.')
    while parts:
        parts = parts[1:]
        if str.join('.', parts) in names:
            return True

    return False


def whitelist_from_url(url: str) -> Set[str]:
    content, trusted = load_from_url(url)

    names, _time_restrictions = parse_list(content, trusted)
    return names


def blacklists_from_config_file(
    file: str, whitelist: str, time_restricted_url: str,
    ignore_retrieval_failure: bool, blacklist_file: str,
) -> None:
    blacklists = {}
    whitelisted_names = set()
    all_names = set()
    unique_names = set()

    # Load conf & blacklists
    with open(file) as fd:
        for line in [*fd.read().splitlines(), f'file:{blacklist_file}']:
            line = str.strip(line)
            if str.startswith(line, '#') or line == '':
                continue
            url = line
            try:
                content, trusted = load_from_url(url)
                names, _time_restrictions = parse_list(content, trusted)
                blacklists[url] = names
                all_names |= names
            except Exception as e:
                sys.stderr.write(
                    getattr(e, 'message') if hasattr(e, 'message') else str(e.args)
                )
                if not ignore_retrieval_failure:
                    exit(1)

    # Time-based blacklist
    if time_restricted_url and not re.match(r'^[a-z0-9]+:', time_restricted_url):
        if os.path.exists(time_restricted_url):
            time_restricted_url = 'file:' + time_restricted_url
        else:
            sys.stderr.write(f'File {time_restricted_url=} does not exist\n')
            time_restricted_url = ''

    if time_restricted_url:
        time_restricted_content, _trusted = load_from_url(time_restricted_url)
        time_restricted_names, time_restrictions = parse_time_restricted_list(
            time_restricted_content
        )

        if time_restricted_names:
            print('########## Time-based blacklist ##########\n')
            for name in time_restricted_names:
                print_restricted_name(name, time_restrictions)

        # Time restricted names should be whitelisted, or they could be always blocked
        whitelisted_names |= time_restricted_names

    # Whitelist
    if whitelist and not re.match(r'^[a-z0-9]+:', whitelist):
        if os.path.exists(whitelist):
            whitelist = 'file:' + whitelist
        else:
            sys.stderr.write(f'File {whitelist=} does not exist\n')
            whitelist = ''

    if whitelist:
        whitelisted_names |= whitelist_from_url(whitelist)

    # Process blacklists
    with open(blacklist_file, 'w') as f:
        for url, names in blacklists.items():
            def p(p: Any) -> None:
                print(p)
                f.write(f'{p}\n')
            p('\n\n########## Blacklist from {} ##########\n'.format(url))
            ignored, whitelisted = 0, 0
            list_names = list()
            for name in names:
                if has_suffix(all_names, name) or name in unique_names:
                    ignored = ignored + 1
                elif has_suffix(whitelisted_names, name) or name in whitelisted_names:
                    whitelisted = whitelisted + 1
                else:
                    list_names.append(name)
                    unique_names.add(name)

            list_names.sort(key=name_cmp)
            if ignored:
                p('# Ignored duplicates: {}\n'.format(ignored))
            if whitelisted:
                p('# Ignored entries due to the whitelist: {}\n'.format(whitelisted))
            if list_names:
                p('# Blacklisted domains: {}\n'.format(len(list_names)))
            for name in list_names:
                f.write(f'{name}\n')


if __name__ == '__main__':
    import argparse

    argp = argparse.ArgumentParser(
        description='Create a unified blacklist from a set of local and remote files'
    )
    argp.add_argument(
        '-c',
        '--config',
        default='domains-blacklist.conf',
        help='file containing blacklist sources',
    )
    argp.add_argument(
        '-w',
        '--whitelist',
        default='domains-whitelist.txt',
        help='file containing a set of names to exclude from the blacklist',
    )
    argp.add_argument(
        '-r',
        '--time-restricted',
        default='domains-time-restricted.txt',
        help='file containing a set of names to be time restricted',
    )
    argp.add_argument(
        '-i',
        '--ignore-retrieval-failure',
        action='store_true',
        help='generate list even if some urls could not be retrieved',
    )
    argp.add_argument(
        '-o',
        '--output-file',
        default='blacklist.txt',
        help='file where blacklist should be written',
    )
    argp.add_argument(
        '-ow',
        '--output-whitelist-file',
        default='whitelist.txt',
        help='file where whitelist should be written',
    )
    argp.add_argument('-t', '--timeout', default=30, help='URL open timeout')
    args = argp.parse_args()

    conf = args.config
    whitelist = args.whitelist
    time_restricted = args.time_restricted
    ignore_retrieval_failure = args.ignore_retrieval_failure or True
    blacklist_file = args.output_file

    blacklists_from_config_file(
        conf, whitelist, time_restricted,
        ignore_retrieval_failure, blacklist_file,
    )
