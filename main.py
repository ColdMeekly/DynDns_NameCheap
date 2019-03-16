import xml.etree.ElementTree as ET
from threading import Timer

import dns.resolver
import urllib3

http = urllib3.PoolManager()
resolver = dns.resolver.Resolver()
resolver.nameservers = ['216.87.155.33']  # NameCheap's dns


# Library for dynamically updating IP addresses

class DynNameCheap:

    def __init__(self, password=None, domain=None):
        if password is None or domain is None:
            raise Exception(f"Either password({password}) or domain({domain}) were not initialised")
        self.response = self.latest_ip = self.active_ip = self.sync_timer = None
        self.password = password
        self.domain = domain

    def __craft_url(self, hostname, ip):
        return f"https://dynamicdns.park-your-domain.com/update?host={hostname}" \
            f"&domain={self.domain}&password={self.password}&ip={ip}"

    def update_host(self, hostname, ip):
        self.response = http.request('GET', self.__craft_url(hostname, ip))

    def success(self):
        if self.response is None:
            return False

        xml = ET.fromstring(self.response.data.decode('utf-8'))
        error_amount = int(xml.find('ErrCount').text)

        if error_amount > 0:
            print("==")
            print(f"ERROR: NameCheap encountered {error_amount} error(s)!")
            for error in xml.find('errors'):
                print(f"<{error.tag}> {error.text}.")
            print("==")
            self.sync_timer.cancel()
            return False

        return xml.find('Done').text == "true"

    def ip_changed(self, hostname):
        try:
            self.active_ip = str(resolver.query(f'{hostname}.{self.domain}', 'A')[0])
        except Exception as e:
            print(f"==\nERROR: DNS resolution failed -> {e}\n==")
            self.sync_timer.cancel()

        if self.active_ip is None:
            return False, False

        self.latest_ip = str(http.request('GET', 'https://api.ipify.org/').data.decode("utf-8"))
        return True, self.latest_ip != self.active_ip

    def __auto_sync(self, hostname, seconds):
        self.sync_timer = Timer(seconds, self.__auto_sync, [hostname, seconds])
        self.sync_timer.start()
        success, changed = self.ip_changed(hostname)
        if not success:
            return
        if not changed:
            print(f"Active IP: {self.active_ip} is the same as your IP: {self.latest_ip}")
            print("Waiting")
            return
        print(f"IP has changed from: _{self.active_ip}_ to -> _{self.latest_ip}_")
        print("Updating")
        self.update_host(hostname, self.latest_ip)
        if self.success():
            print("Success!")
        else:
            print("Mission Failed!")

    def auto_sync(self, hostname=None, seconds=60):
        if hostname is None:
            return
        print("Starting Sync..")
        self.__auto_sync(hostname, seconds)


# Example usage: Sync current machine with any subdomain
if __name__ == "__main__":
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Initialize the updater

    updater = DynNameCheap(
        password="DYN_DNS_KEY",  # This is found in the advancedns section
        domain="example.com"  # This is a domain that you own
    )

    # Sync development.example.com every 30 seconds
    updater.auto_sync("cubeworldd", 30)
