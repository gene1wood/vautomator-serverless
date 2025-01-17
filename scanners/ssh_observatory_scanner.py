import requests
import time
import os
import logging


class SSHObservatoryScanner():

    def __init__(self, poll_interval=1, logger=logging.getLogger(__name__)):
        self.session = requests.Session()
        self.poll_interval = poll_interval
        self.api_url = os.getenv('SSHOBS_API_URL')
        self.logger = logger

    def scan(self, hostname):
        # Initiate the scan
        if self.api_url[-1] != "/":
            analyze_url = self.api_url + '/scan?target=' + hostname
            self.logger.info("Running SSH Observatory scan on {}...".format(hostname))
            results = {}
            scan_id = self.session.post(analyze_url, data=None).json()['uuid']

            # Wait for the scan to complete, polling every second
            results['scan'] = self.__poll(scan_id)
            results['host'] = hostname
            return results
        else:
            raise Exception("Invalid API URL specified for Observatory.")

    def __poll(self, scan_id):
        url = self.api_url + '/scan/results?uuid=' + str(scan_id)
        resp = None
        count = 0
        while count < 30:
            resp = self.session.get(url).json()
            # This means we got our results back, so return them!
            if 'ssh_scan_version' in resp:
                return resp

            time.sleep(self.poll_interval)
            count += 1
        self.logger.warning(
            "Unable to get SSH Observatory scan results within {} seconds, or SSH service is not running on target ".format(count)
        )
        return resp
