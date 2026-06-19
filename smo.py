#!/usr/bin/env python3
"""
UserSleuth - Social Media Username Availability Checker
Checks whether a given username exists across multiple social platforms.
For OSINT / ethical recon use only.
"""

import argparse
import sys
import concurrent.futures
import requests
from colorama import Fore, Style, init

init(autoreset=True)

# Platform map: name -> (profile_url, expects_404_on_missing)
PLATFORMS = {
    'instagram': 'https://www.instagram.com/{}/',
    'facebook':  'https://www.facebook.com/{}',
    'twitter':   'https://twitter.com/{}',
    'x':         'https://x.com/{}',
    'youtube':   'https://www.youtube.com/@{}',
    'tiktok':    'https://www.tiktok.com/@{}',
    'github':    'https://github.com/{}',
    'reddit':    'https://www.reddit.com/user/{}',
    'telegram':  'https://t.me/{}',
    'pinterest': 'https://www.pinterest.com/{}/',
    'tumblr':    'https://{}.tumblr.com',
    'medium':    'https://medium.com/@{}',
    'twitch':    'https://www.twitch.tv/{}',
    'steam':     'https://steamcommunity.com/id/{}',
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
}

BANNER = rf"""{Fore.CYAN}
 _   _              ____  _           _   _
| | | |___  ___ _ _/ ___|| | ___ _   _| |_| |__
| | | / __|/ _ \ '_\___ \| |/ _ \ | | | __| '_ \
| |_| \__ \  __/ |  ___) | |  __/ |_| | |_| | | |
 \___/|___/\___|_| |____/|_|\___|\__,_|\__|_| |_|
{Style.RESET_ALL}{Fore.YELLOW}     Social Media Username Checker (OSINT){Style.RESET_ALL}
"""


def check_platform(platform, username, timeout=6):
    """Check a single platform for a given username. Returns (platform, status, url)."""
    url = PLATFORMS[platform].format(username)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        # NOTE: status codes alone are unreliable across platforms.
        # Many sites return 200 for both valid and invalid profiles (SPA shells),
        # so this is a heuristic, not a guarantee. Always verify manually.
        if resp.status_code == 200:
            return platform, "FOUND", url
        elif resp.status_code == 404:
            return platform, "NOT_FOUND", url
        else:
            return platform, f"UNKNOWN ({resp.status_code})", url
    except requests.exceptions.Timeout:
        return platform, "TIMEOUT", url
    except requests.exceptions.RequestException:
        return platform, "ERROR", url


def run_check(username, platforms, timeout=6, max_workers=8):
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(check_platform, p, username, timeout): p
            for p in platforms
        }
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    return results


def print_result(platform, status, url):
    label = platform.upper().ljust(10)
    if status == "FOUND":
        print(f"{Fore.GREEN}[+] {label} EXISTS    -> {url}{Style.RESET_ALL}")
    elif status == "NOT_FOUND":
        print(f"{Fore.RED}[-] {label} NOT FOUND -> {url}{Style.RESET_ALL}")
    elif status == "TIMEOUT":
        print(f"{Fore.YELLOW}[!] {label} TIMEOUT   -> {url}{Style.RESET_ALL}")
    else:
        print(f"{Fore.MAGENTA}[?] {label} {status:<10} -> {url}{Style.RESET_ALL}")


def interactive_mode():
    print(BANNER)
    names = list(PLATFORMS.keys())
    print("Available platforms:")
    for i, p in enumerate(names, start=1):
        print(f"  {i}. {p}")
    print(f"  {len(names)+1}. ALL")

    choice = input("\nSelect platform number: ").strip()
    username = input("Enter username to check: ").strip()

    if not username:
        print(f"{Fore.RED}Username cannot be empty.{Style.RESET_ALL}")
        sys.exit(1)

    try:
        idx = int(choice)
    except ValueError:
        print(f"{Fore.RED}Invalid choice.{Style.RESET_ALL}")
        sys.exit(1)

    if idx == len(names) + 1:
        selected = names
    elif 1 <= idx <= len(names):
        selected = [names[idx - 1]]
    else:
        print(f"{Fore.RED}Invalid choice.{Style.RESET_ALL}")
        sys.exit(1)

    print(f"\n{Fore.CYAN}Checking '{username}' across {len(selected)} platform(s)...{Style.RESET_ALL}\n")
    results = run_check(username, selected)
    for platform, status, url in sorted(results, key=lambda r: r[0]):
        print_result(platform, status, url)


def cli_mode():
    parser = argparse.ArgumentParser(
        description="UserSleuth - Check username availability across social platforms (OSINT tool)."
    )
    parser.add_argument("username", help="Username to check")
    parser.add_argument(
        "-p", "--platforms",
        help="Comma-separated list of platforms to check (default: all). "
             f"Choices: {', '.join(PLATFORMS.keys())}",
        default="all"
    )
    parser.add_argument(
        "-t", "--timeout", type=int, default=6,
        help="Request timeout in seconds (default: 6)"
    )
    parser.add_argument(
        "-o", "--output", help="Save results to a file (e.g. results.txt)"
    )
    args = parser.parse_args()

    if args.platforms.lower() == "all":
        selected = list(PLATFORMS.keys())
    else:
        selected = [p.strip().lower() for p in args.platforms.split(",")]
        invalid = [p for p in selected if p not in PLATFORMS]
        if invalid:
            print(f"{Fore.RED}Unknown platform(s): {', '.join(invalid)}{Style.RESET_ALL}")
            print(f"Available: {', '.join(PLATFORMS.keys())}")
            sys.exit(1)

    print(BANNER)
    print(f"{Fore.CYAN}Checking '{args.username}' across {len(selected)} platform(s)...{Style.RESET_ALL}\n")

    results = run_check(args.username, selected, timeout=args.timeout)
    results.sort(key=lambda r: r[0])

    lines = []
    for platform, status, url in results:
        print_result(platform, status, url)
        lines.append(f"{platform}: {status} -> {url}")

    if args.output:
        with open(args.output, "w") as f:
            f.write(f"UserSleuth results for username: {args.username}\n\n")
            f.write("\n".join(lines))
        print(f"\n{Fore.CYAN}Results saved to {args.output}{Style.RESET_ALL}")


def main():
    if len(sys.argv) > 1:
        cli_mode()
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
