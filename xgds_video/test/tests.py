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

from django.test import TransactionTestCase
from django.core.urlresolvers import reverse

class xgds_videoTest(TransactionTestCase):
    """
    Tests for xgds_video
    """
    filepath = '/home/xgds/xgds_subsea/apps/xgds_video/test/test_files/na1.stream_2018-09-02-22.58.45.785-UTC_65'
    ref_2 = filepath + '/Screenshot_2018.09.02-22.58.52.png'

    def test_xgds_video(self):
        # print "testing git hook 7 in xgds_video"
        pass

    def test_frame_grab(self):
        """
        Test getting image bytes from a series of .ts files
        """
        response = self.client.post(reverse('grab_frame_nickname'),
                                    {'path': xgds_videoTest.filepath,
                                     'start_time': '20180902 22:58:45',
                                     'grab_time': '20180902 22:58:52'})
        with open(xgds_videoTest.ref_2, 'rb') as f:
            reference_bytes_2 = f.read()
            f.close()

        pic = response.content
        equals_reference = (pic == reference_bytes_2)
        self.assertTrue(equals_reference)