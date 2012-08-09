'''
Tests for DDI harvester
'''
import logging
import os
import unittest
import mock
import urllib2
from StringIO import StringIO
import json
import uuid
import pprint

import testdata

from lxml import etree

from ckan.model import Session, Package, Resource, Group

from ckan.tests.functional.base import FunctionalTestCase

from ckanext.ddi.harvester import DDIHarvester
from ckanext.harvest.model import HarvestJob, HarvestSource, HarvestObject,\
                                  setup
log = logging.getLogger(__file__)
class TestDDIHarvester(unittest.TestCase, FunctionalTestCase):

    @classmethod
    def setup_class(self):
        setup()
    @classmethod
    def teardown_class(self):
        Session.remove()

    def _create_harvester(self):
        harv = DDIHarvester()
        harv.config = "{}"
        harvest_job = HarvestJob()
        harvest_job.source = HarvestSource()
        harvest_job.source.title = "Test"
        harvest_job.source.url = "http://foo"
        harvest_job.source.config = ''
        harvest_job.source.type = "DDI"
        Session.add(harvest_job)
        return harv, harvest_job

    def test_harvester_info(self):
        harv, job = self._create_harvester()
        self.assert_(isinstance(harv.info(),dict))
        self.assert_(harv.validate_config(harv.config))

    def test_harvester_create(self):
        harv, job = self._create_harvester()
        self.assert_(harv)
        self.assert_(job)
        self.assert_(job.source)
        self.assert_(job.source.title == "Test")

    def test_harvester_gather(self):
        harv, job = self._create_harvester()
        res = """
        http://www.fsd.uta.fi/fi/aineistot/luettelo/FSD0115/FSD0115.xml
        """
        urllib2.urlopen = mock.Mock(return_value=StringIO(res))
        gathered = harv.gather_stage(job)
        self.assert_(len(gathered) != 0)
        uid = uuid.UUID(gathered[0])
        self.assert_(str(uid))

    def test_harvester_fetch(self):
        harv, job = self._create_harvester()
        res = """
        http://www.fsd.uta.fi/fi/aineistot/luettelo/FSD0115/FSD0115.xml
        """
        urllib2.urlopen = mock.Mock(return_value=StringIO(res))
        gathered = harv.gather_stage(job)
        urllib2.urlopen = mock.Mock(return_value=StringIO(testdata.nr1))
        harvest_obj = HarvestObject.get(gathered[0])
        self.assert_(harv.fetch_stage(harvest_obj))
        self.assert_(isinstance(json.loads(harvest_obj.content), dict))
        result = json.loads(harvest_obj.content)
        self.assert_("stdyDscr" in result['codeBook'])
        urllib2.urlopen = mock.Mock(return_value=StringIO(testdata.foobar))
        harvest_obj = HarvestObject.get(gathered[0])
        self.assert_(not harv.fetch_stage(harvest_obj))

    def test_harvester_import(self):
        harv, job = self._create_harvester()
        res = """
        http://www.fsd.uta.fi/fi/aineistot/luettelo/FSD0115/FSD0115.xml
        """
        urllib2.urlopen = mock.Mock(return_value=StringIO(res))
        gathered = harv.gather_stage(job)
        urllib2.urlopen = mock.Mock(return_value=StringIO(testdata.nr1))
        harvest_obj = HarvestObject.get(gathered[0])
        self.assert_(harv.fetch_stage(harvest_obj))
        self.assert_(isinstance(json.loads(harvest_obj.content), dict))
        self.assert_(harv.import_stage(harvest_obj))
        self.assert_(len(Session.query(Package).all()) == 1)

        # Lets see if the package is ok, according to test data
        pkg = Session.query(Package).all()[0]
        self.assert_(pkg.name == "Puolueiden ajankohtaistutkimus 1981")
        self.assert_(len(pkg.get_groups()) == 2)
        self.assert_(len(pkg.resources) == 1)

        urllib2.urlopen = mock.Mock(return_value=StringIO(testdata.nr2))
        harvest_obj = HarvestObject.get(gathered[0])
        self.assert_(harv.fetch_stage(harvest_obj))
        self.assert_(isinstance(json.loads(harvest_obj.content), dict))
        self.assert_(harv.import_stage(harvest_obj))
        self.assert_(len(Session.query(Package).all()) == 2)
