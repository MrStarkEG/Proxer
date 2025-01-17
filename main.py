import os
import re
from pathlib import Path
from datetime import datetime
from typing import Set, List, Dict
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init


class ProxyManager:
    PROXY_SOURCES: Dict[str, str] = {
        'sslproxies': 'https://www.sslproxies.org/',
        'freeproxylist': 'https://free-proxy-list.net/',
        'usproxy': 'https://www.us-proxy.org/',
        'socksproxy': 'https://www.socks-proxy.net/',
        'spysme': 'https://spys.me/proxy.txt',
        'proxydaily': 'https://proxy-daily.com/'
    }

    OUTPUT_DIR = Path("ProxerProxies")
    TEST_URL = 'https://httpbin.org/ip'
    TIMEOUT = 5
    MAX_WORKERS = 50

    def __init__(self):
        init(autoreset=True)
        self.OUTPUT_DIR.mkdir(exist_ok=True)

    @staticmethod
    def get_timestamp() -> str:
        return datetime.now().strftime('%Y-%m-%d-%I-%M-%S%p')

    def save_proxies(self, proxies: Set[str], prefix: str = "") -> Path:
        timestamp = self.get_timestamp()
        file_path = self.OUTPUT_DIR / f"{prefix}_{timestamp}.txt"
        with open(file_path, 'w') as f:
            f.write('\n'.join(proxies))
        print(f"{Fore.GREEN}Proxies saved to {file_path}{Style.RESET_ALL}")

    def save_valid_proxies(self, proxies: List[str], prefix: str = "valid") -> Path:
        timestamp = self.get_timestamp()
        file_path = self.OUTPUT_DIR / f"{prefix}_{timestamp}.txt"
        with open(file_path, 'w') as f:
            for proxy in proxies:
                f.write(f'{proxy}\n')
        print(f"{Fore.GREEN}Valid proxies saved to {
              file_path}{Style.RESET_ALL}")

    def parse_spysme(self, response_text: str) -> Set[str]:
        return {
            proxy for proxy in response_text.splitlines()
            if re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', proxy)
        }

    def parse_html_table(self, soup: BeautifulSoup) -> Set[str]:
        proxies = set()
        for row in soup.find_all('tr'):
            columns = row.find_all('td')
            if columns and re.match(r'^\d+\.\d+\.\d+\.\d+$', columns[0].text) and columns[1].text.isdigit():
                proxies.add(f'{columns[0].text}:{columns[1].text}')
        return proxies

    def get_proxies(self, sources: List[str] = None) -> Set[str]:
        if sources is None:
            sources = list(self.PROXY_SOURCES.keys())

        invalid_sources = set(sources) - set(self.PROXY_SOURCES.keys())
        if invalid_sources:
            raise ValueError(f"Invalid sources specified: {invalid_sources}")

        proxies = set()
        for source in sources:
            try:
                response = requests.get(self.PROXY_SOURCES[source])
                response.raise_for_status()

                if source == 'spysme':
                    proxies.update(self.parse_spysme(response.text))
                else:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    proxies.update(self.parse_html_table(soup))

            except requests.RequestException as e:
                print(f"{Fore.RED}Error fetching from {
                      source}: {e}{Style.RESET_ALL}")
                continue

        self.save_proxies(proxies)
        return proxies

    def test_proxy(self, proxy: str) -> bool:
        try:
            response = requests.get(
                self.TEST_URL,
                proxies={'http': proxy, 'https': proxy},
                timeout=self.TIMEOUT
            )
            if response.status_code == 200 and 'origin' in response.text:
                print(f"{Fore.GREEN}Working proxy: {proxy}{Style.RESET_ALL}")
                return True
        except:
            pass
        print(f"{Fore.RED}Invalid proxy: {proxy}{Style.RESET_ALL}")
        return False

    def filter_proxies(self, proxies: Set[str]) -> List[str]:
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            results = executor.map(self.test_proxy, proxies)
            valid = []
            for proxy, is_working in zip(proxies, results):
                if is_working:
                    # self.save_valid_proxies(proxy)
                    valid.append(proxy)
        return valid


class ProxyCLI:
    BANNER = """
    ██████╗ ██████╗  ██████╗ ██╗  ██╗███████╗██████╗
    ██╔══██╗██╔══██╗██╔═══██╗╚██╗██╔╝██╔════╝██╔══██╗
    ██████╔╝██████╔╝██║   ██║ ╚███╔╝ █████╗  ██████╔╝
    ██╔═══╝ ██╔══██╗██║   ██║ ██╔██╗ ██╔══╝  ██╔══██╗
    ██║     ██║  ██║╚██████╔╝██╔╝ ██╗███████╗██║  ██║
    ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
                    V 1.1.3
    """

    def __init__(self):
        self.proxy_manager = ProxyManager()

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def get_proxies_menu(self):
        print(f"{Fore.CYAN}Select The Source{Style.RESET_ALL}")
        choice = input(
            f"{Fore.CYAN}1- sslproxies\n2- freeproxylist\n3- ALL\n>> {Style.RESET_ALL}")

        sources_map = {
            "1": ['sslproxies'],
            "2": ['freeproxylist'],
            "3": list(ProxyManager.PROXY_SOURCES.keys())
        }

        if choice not in sources_map:
            raise ValueError(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")

        proxies = self.proxy_manager.get_proxies(sources_map[choice])
        print(f"{Fore.GREEN}Collected {len(proxies)
                                       } proxies from selected sources.{Style.RESET_ALL}")

    def check_proxies_menu(self):
        file_path = input(f"{Fore.CYAN}Enter the path to the proxy file: {
                          Style.RESET_ALL}")
        try:
            with open(file_path, 'r') as f:
                proxies = set(f.read().splitlines())
        except FileNotFoundError:
            raise ValueError(f"{Fore.RED}File not found.{Style.RESET_ALL}")

        working_proxies = self.proxy_manager.filter_proxies(proxies)
        print(f"{Fore.GREEN}Found {len(working_proxies)
                                   } working proxies.{Style.RESET_ALL}")
        self.proxy_manager.save_proxies(
            working_proxies, prefix="working_proxies")

    def run(self):
        self.clear_screen()
        print(self.BANNER)
        print(f"{Fore.CYAN}Select What you need <3{Style.RESET_ALL}")
        choice = input(
            f"{Fore.CYAN}1- Get Proxies\n2- Check Proxies\n>> {Style.RESET_ALL}")

        try:
            if choice == "1":
                self.get_proxies_menu()
            elif choice == "2":
                self.check_proxies_menu()
            else:
                raise ValueError(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
        except Exception as e:
            print(str(e))


def main():
    try:
        cli = ProxyCLI()
        cli.run()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Program terminated by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}An unexpected error occurred: {e}{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
