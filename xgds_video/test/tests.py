#__BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
#
# The xGDS platform is licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR

# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#__END_LICENSE__

import subprocess
import os
import shutil
from django.test import TransactionTestCase
from django.core.urlresolvers import reverse
from geocamUtil.loader import LazyGetModelByName, getClassByName
from django.conf import settings
from dateutil.parser import parse as dateparser
from xgds_video.frame_grab import *


class xgds_videoTest(TransactionTestCase):
    """
    Tests for xgds_video
    """
    filepath = '/home/xgds/xgds_subsea/apps/xgds_video/test/test_files/na1.stream_2018-09-02-22.58.45.785-UTC_65'
    ref_2 = filepath + '/Screenshot_2018.09.02-22.58.52.png'

    ts_1 = filepath + '/fileSequence0.ts'
    ref_1 = filepath + '/Screenshot_2018.09.02-22.58.47.png'
    ref_2 = filepath + '/Screenshot_2018.09.02-22.58.52.png'


    fixtures = ['geocamTrack_initial_data.json',
                'xgds_core_initial_data.json',
                'xgds_core_testing.json',
                'test_cameras.json',
                'test_h1708_herc_track.json',
                'test_h1708_herc_positions.json',
                'test_h1708_herc_flight.json',
                'test_users.json']

    @classmethod
    def setUpClass(self):
        # Keep track of the global default vehicle pk and set the global to
        # what these tests need it to be
        self.default_vehicle_pk = settings.XGDS_CORE_DEFAULT_VEHICLE_PK
        settings.XGDS_CORE_DEFAULT_VEHICLE_PK = 1
        settings.COUCHDB_FILESTORE_NAME = "test-file-store"
        db_url = '%s/%s' % (settings.COUCHDB_URL, settings.COUCHDB_FILESTORE_NAME)
        # create the couchdb
        subprocess.call([
            "curl", "-X", "PUT", db_url
        ], shell=False)

    @classmethod
    def tearDownClass(self):
        # Restore the global variable we changed during setup
        settings.XGDS_CORE_DEFAULT_VEHICLE_PK = self.default_vehicle_pk
        db_url = '%s/test-file-store' % (settings.COUCHDB_URL)
        # delete the couchdb
        subprocess.call([
            "curl", "-X", "DELETE", db_url
        ], shell=False)

        # clean up vips tiles
        deepzoom_path = '/home/xgds/xgds_subsea/data/xgds_image/deepzoom_images/test_grab_20180902 22:58:52_deepzoom_1'

        if os.path.exists(deepzoom_path):
            shutil.rmtree(deepzoom_path)

    def test_take_screenshot(self):
        bytes = take_screenshot(xgds_videoTest.ts_1, 2)

        with open(xgds_videoTest.ref_1, 'rb') as f:
            reference_bytes = f.read()
            f.close()

        # doing this so it does not print obnoxious binary
        # if the test fails
        equals_reference = (bytes == reference_bytes)
        self.assertTrue(equals_reference)

    def test_grab_frame(self):

        # path, start, grab
        bytes = grab_frame(xgds_videoTest.filepath,
                           dateparser('20180902 22:58:45'),
                           dateparser('20180902 22:58:52'))

        with open(xgds_videoTest.ref_2, 'rb') as f:
            reference_bytes_2 = f.read()
            f.close()

        equals_reference = (bytes == reference_bytes_2)
        self.assertTrue(equals_reference)

        # path, hms
        bytes = grab_frame(xgds_videoTest.filepath,
                           hms='00:00:07')

        equals_reference = (bytes == reference_bytes_2)
        self.assertTrue(equals_reference)

        # file, hms
        bytes = grab_frame(file=xgds_videoTest.ts_1,
                           hms='00:00:02')

        with open(xgds_videoTest.ref_1, 'rb') as f:
            reference_bytes_1 = f.read()
            f.close()

        equals_reference = (bytes == reference_bytes_1)
        self.assertTrue(equals_reference)

    def test_exceptions(self):
        # path, grab, no start
        with self.assertRaises(Exception):
            bytes = grab_frame(xgds_videoTest.filepath,
                               grab_time=dateparser('20180902 22:58:52'))

        # no grab, no start
        with self.assertRaises(Exception):
            bytes = grab_frame(xgds_videoTest.filepath)

    def test_frame_grab_and_insert_database(self):
        """
        Test grabbing a video frame and inserting it into the CouchDB
        """
        grab_time_str = '20180902 22:58:52'
        start_time_str = '20180902 22:58:45'
        vehicle_name = 'Generic Vehicle'

        response = self.client.post(reverse('grab_frame_save_image'),
                                    {'path': xgds_videoTest.filepath,
                                     'start_time': start_time_str,
                                     'grab_time': grab_time_str,
                                     'vehicle': vehicle_name,
                                     'camera': 'Hercules',
                                     'username': 'xgds',
                                     'filename_prefix': 'test_grab'
                                     })

        shortname = 'test_grab_20180902 22:58:52.png'
        found = LazyGetModelByName(settings.XGDS_IMAGE_IMAGE_SET_MODEL).get().objects.get(name=shortname)

        with open(xgds_videoTest.ref_2, 'rb') as f:
            reference_bytes_2 = f.read()
            f.close()

        # found is an ImageSet, get its raw image bytes
        raw_image = found.getRawImage()
        raw_image_file = raw_image.file
        found_bytes = raw_image_file.read()
        raw_image_file.close()

        equals_reference = (found_bytes == reference_bytes_2)
        self.assertTrue(equals_reference)

    def test_frame_grab(self):
        """
        Test getting image bytes from a series of .ts files
        """
        response = self.client.post(reverse('grab_frame'),
                                    {'path': xgds_videoTest.filepath,
                                     'start_time': '20180902 22:58:45',
                                     'grab_time': '20180902 22:58:52',})
        with open(xgds_videoTest.ref_2, 'rb') as f:
            reference_bytes_2 = f.read()
            f.close()

        pic = response.content
        equals_reference = (pic == reference_bytes_2)
        self.assertTrue(equals_reference)