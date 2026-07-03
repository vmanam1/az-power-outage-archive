import unittest
from unittest.mock import Mock, patch
from xml.etree import ElementTree

from providers.ed3 import ED3Provider


SAMPLE_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<MobileOutageInfo xmlns="http://tempuri.org/">
  <Outages>
    <MobileOutage>
      <X>-111.95</X>
      <Y>33.05</Y>
      <CutomersAffected>12</CutomersAffected>
      <OutageTime>07/02/2026 03:15:00 PM</OutageTime>
      <PoleNumber>P-123</PoleNumber>
      <CaseStatus>Crew Assigned</CaseStatus>
      <Cause>Equipment Failure</Cause>
      <RestorationTime>07/02/2026 05:00:00 PM</RestorationTime>
      <ElementName>Maricopa</ElementName>
    </MobileOutage>
  </Outages>
  <TotalCustAffected>12</TotalCustAffected>
  <TotalCustomers>36,318</TotalCustomers>
</MobileOutageInfo>
"""


class ED3ProviderTests(unittest.TestCase):
    @patch("providers.ed3.requests.get")
    def test_fetches_and_formats_xml_feed(self, get):
        response = Mock(content=SAMPLE_XML)
        get.return_value = response

        result = ED3Provider().fetch_data()

        get.assert_called_once_with(ED3Provider.API_URL, timeout=30)
        response.raise_for_status.assert_called_once_with()
        self.assertEqual(result["metadata"]["provider"], "ED3")
        self.assertEqual(result["summary"]["outage_count"], 1)
        self.assertEqual(result["summary"]["customers_affected"], 12)
        self.assertEqual(result["summary"]["total_customers"], 36318)
        outage = result["outages"][0]
        self.assertEqual(outage["latitude"], 33.05)
        self.assertEqual(outage["longitude"], -111.95)
        self.assertEqual(outage["start_time"], "2026-07-02 15:15:00 MST")
        self.assertEqual(outage["etr"], "2026-07-02 17:00:00 MST")

    def test_malformed_customer_count_is_not_treated_as_zero(self):
        malformed = SAMPLE_XML.replace(
            b"<CutomersAffected>12</CutomersAffected>",
            b"<CutomersAffected>unknown</CutomersAffected>",
        )
        with self.assertRaisesRegex(ValueError, "valid customer count"):
            ED3Provider().parse_xml(ElementTree.fromstring(malformed))


if __name__ == "__main__":
    unittest.main()
