# __BEGIN_LICENSE__
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
# __END_LICENSE__

from django.test import TestCase
from xgds_video.frame_grab import *

class TestFrameGrab(TestCase):
    filepath = '/home/xgds/xgds_subsea/apps/xgds_video/test/test_files/na1.stream_2018-09-02-22.58.45.785-UTC_65'
    ts_1 = filepath + '/fileSequence0.ts'
    ref_1 = filepath + '/Screenshot_2018.09.02-22.58.47.png'
    ref_2 = filepath + '/Screenshot_2018.09.02-22.58.52.png'

    def test_take_screenshot(self):
        bytes = take_screenshot(TestFrameGrab.ts_1, 2)

        with open(TestFrameGrab.ref_1, 'rb') as f:
            reference_bytes = f.read()
            f.close()

        # doing this so it does not print obnoxious binary
        # if the test fails
        equals_reference = (bytes == reference_bytes)
        self.assertTrue(equals_reference)

    def test_grab_frame(self):
        # path, start, grab
        bytes = grab_frame(TestFrameGrab.filepath,
                           dateparser('20180902 22:58:45'),
                           dateparser('20180902 22:58:52'))

        with open(TestFrameGrab.ref_2, 'rb') as f:
            reference_bytes_2 = f.read()
            f.close()

        equals_reference = (bytes == reference_bytes_2)
        self.assertTrue(equals_reference)

        # path, hms
        bytes = grab_frame(TestFrameGrab.filepath,
                           hms='00:00:07')

        equals_reference = (bytes == reference_bytes_2)
        self.assertTrue(equals_reference)

        # file, hms
        bytes = grab_frame(file=TestFrameGrab.ts_1,
                           hms='00:00:02')

        with open(TestFrameGrab.ref_1, 'rb') as f:
            reference_bytes_1 = f.read()
            f.close()

        equals_reference = (bytes == reference_bytes_1)
        self.assertTrue(equals_reference)

    def test_exceptions(self):
        # path, grab, no start
        with self.assertRaises(Exception):
            bytes = grab_frame(TestFrameGrab.filepath,
                            grab_time=dateparser('20180902 22:58:52'))

        # no grab, no start
        with self.assertRaises(Exception):
            bytes = grab_frame(TestFrameGrab.filepath)
















