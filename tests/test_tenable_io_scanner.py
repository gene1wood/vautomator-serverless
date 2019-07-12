import sys
import pytest
import os
import json
import requests
import boto3
from scanners.tenable_io_scanner import TIOScanner
from lib.custom_exceptions import TenableScanRunningException, TenableScanUnexpectedStateException, TenableScanInterruptedException
from lib.target import Target
from moto import mock_ssm
from tenable_io.client import TenableIOClient
from tenable_io.exceptions import TenableIOApiException, TenableIOErrorCode
from tenable_io.api.scans import ScanExportRequest
from tenable_io.api.models import Scan


class TestTIOScanner():
    # Approach taken here is to create a dedicated Tenable.io
    # account just for test purposes, and use Travis CI's
    # "secure" method to store the credentials, use those
    # credentials to test the "scan" method.

    # Mocking SSM here so we can test the __getAPIKey() method
    @pytest.fixture
    def ssm(self, scope="session", autouse=True):
        mock = mock_ssm()
        mock.start()
        # There is currently a bug on moto, this line is needed as a workaround
        # Ref: https://github.com/spulec/moto/issues/1926
        boto3.setup_default_session()

        ssm_client = boto3.client('ssm', 'us-west-2')
        ssm_client.put_parameter(
            Name="TENABLEIO_ACCESS_KEY",
            Description="Bogus access key.",
            Value="TEST",
            Type="SecureString"
        )

        ssm_client.put_parameter(
            Name="TENABLEIO_SECRET_KEY",
            Description="Bogus secret key.",
            Value="TEST",
            Type="SecureString"
        )

        yield ssm_client
        mock.stop()

    def test_defaults(self, ssm):
        scanner = TIOScanner(ssm_client=ssm)
        assert scanner.client is None
        assert scanner.tio_access_key is None
        assert scanner.tio_secret_key is None
        assert scanner.report_format == "html"
        assert scanner.ssm_client == ssm

    def test_tenable_auth_fail(self):
        try:
            TenableIOClient('test', 'test').session_api.get()
            assert False
        except TenableIOApiException as e:
            assert e.code is TenableIOErrorCode.UNAUTHORIZED

    # This will work in Travis, because we use secure
    # env variables to store API keys. Let's not risk
    # leaking them locally, so do not run this if
    # running locally (i.e. only run in Travis)
    @pytest.mark.skipif("TRAVIS" not in os.environ
                        and not os.getenv("TRAVIS"),
                        reason="Only run this test on Travis CI.")
    def test_tenable_auth_success(self):
        # See if the keys are available as env variables
        try:
            a_key = os.environ["TIOA"]
            s_key = os.environ["TIOS"]
        except Exception:
            assert False
        # See if we can use those keys to successfully
        # authenticate to Tenable.io, should be True
        try:
            TenableIOClient(a_key, s_key).session_api.get()
            assert True
        except TenableIOApiException as e:
            assert e.code is TenableIOErrorCode.UNAUTHORIZED

    # This will work in Travis, because we use secure
    # env variables to store API keys. Let's not risk
    # leaking them locally, so do not run this if
    # running locally (i.e. only run in Travis)
    @pytest.mark.skipif("TRAVIS" not in os.environ
                        and not os.getenv("TRAVIS"),
                        reason="Only run this test on Travis CI.")
    def test_scan(self):
        # See if the keys are available as env variables
        try:
            a_key = os.environ["TIOA"]
            s_key = os.environ["TIOS"]
        except Exception:
            assert False
        host_name = "www.mozilla.org"
        scanner = TIOScanner(access_key=a_key, secret_key=s_key)
        nscan = scanner.scan(host_name)

        # Ref: https://github.com/tenable/Tenable.io-SDK-for-Python/blob/master/tests/integration/helpers/test_scan.py
        # nscan is a ScanRef object.
        # Note that we are NOT launching the scan here, we do not
        # want an actual scan to be kicked off as a part of CI
        # scan_details is a scan_detail object
        scan_detail = nscan.details()
        # ScanRef object ID should the ScanDetail object ID
        assert scan_detail.info.object_id == nscan.id
        nscan.delete(force_stop=True)

    # This will work in Travis, because we use secure
    # env variables to store API keys. Let's not risk
    # leaking them locally, so do not run this if
    # running locally (i.e. only run in Travis)
    @pytest.mark.skipif("TRAVIS" not in os.environ
                        and not os.getenv("TRAVIS"),
                        reason="Only run this test on Travis CI.")
    def test_scanResult(self):
        # See if the keys are available as env variables
        try:
            a_key = os.environ["TIOA"]
            s_key = os.environ["TIOS"]
        except Exception:
            assert False
        # Let's select a known scan ID here
        # this one is completed
        scan_id_completed = 453
        # This one is cancelled
        scan_id_aborted = 715

        scanner = TIOScanner(access_key=a_key, secret_key=s_key)
        result_as_json = scanner.scanResult(scan_id_completed)
        assert type(result_as_json) is dict
        assert 'hosts' in result_as_json
        assert 'history' in result_as_json
        assert 'info' in result_as_json
        result_as_html = scanner.scanResult(scan_id_completed, result_format="html")
        assert type(result_as_html) is str
        assert "html" in result_as_html
        assert "tenable" in result_as_html
        assert "plugin" in result_as_html

        with pytest.raises(TenableScanInterruptedException) as e:
            assert scanner.scanResult(scan_id_aborted)
        assert str(e.value) == "Tenable.io scan ended abruptly, likely stopped or aborted manually."

    def test__getAPIKey(self, ssm):
        scanner = TIOScanner(ssm_client=ssm)
        test_akey, test_skey = scanner._TIOScanner__getAPIKey()
        try:
            a_key = os.environ["TIOA"]
            s_key = os.environ["TIOS"]
        except Exception:
            assert test_akey == "TEST"
            assert test_skey == "TEST"
        else:
            assert test_akey == a_key
            assert test_skey == s_key

    def test__createClient(self, ssm):
        scanner = TIOScanner(ssm_client=ssm)
        client = scanner._TIOScanner__createClient()
        assert type(client) is TenableIOClient

        nscanner = TIOScanner(access_key='test', secret_key='test')
        nclient = nscanner._TIOScanner__createClient()
        assert type(nclient) is TenableIOClient
