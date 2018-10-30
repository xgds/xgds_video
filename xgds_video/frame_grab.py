#!/usr/bin/env python
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

import ffmpeg
import argparse
import m3u8
import os
from dateutil.parser import parse as dateparser


# D make take_screenshot return buffer of bytes
# D make main save those bytes to a file
# D make a callable function that acts like main (test on commandline with import)
# make prog index a parameter
# D make it save with a UTC YYYY-MM-DD hhmmss and option pre-tag (vessel name?)
def take_screenshot(input_file, seconds_into):
    out, _ = (
        ffmpeg. \
        input(input_file, ss=seconds_into). \
        output('pipe:', vframes=1, format='image2', vcodec='png'). \
        run(capture_stdout=True, quiet=True)
    )
    return out


def calculate_ts_file(folder_name, s_int, index_file_name):
    # open the prog_index.m3u8
    m3u8_obj = m3u8.load(os.path.join(folder_name, index_file_name))

    acc_time = 0
    num_segs = len(m3u8_obj.segments)
    s_float = float(s_int)
    file_number = 0
    for seg_num in range(0, num_segs):
        next_delta = m3u8_obj.segments[seg_num].duration
        if acc_time + next_delta > float(s_float):
            # save file number
            # (if you subtract 1, you're off by one. not sure why.)
            file_number = seg_num
            break
        acc_time = acc_time + next_delta
        
    if s_int > int(acc_time + next_delta):
        print "**** Requested time "+str(s_int)+"s is outside range of prog_index.m3u8, "\
              +str(int(acc_time + next_delta))+'s ****'
        exit -1

    return m3u8_obj.segments[file_number].uri, s_float - acc_time


def hms_to_total_s(hms_string):
    tokens = hms_string.split(':')
    if len(tokens) == 3:
        h = tokens[0]
        m = tokens[1]
        s = tokens[2]
    elif len(tokens) == 2 :
        h = 0
        m = tokens[0]
        s = tokens[1]
    elif len(tokens) == 1 :
        h = 0
        m = 0
        s = tokens[0]
    ans = int(s) + int(m)*60 + int(h)*60*60
    return ans


def grab_frame(path, start_time, grab_time, file=None, hms=None, index_file_name='prog_index.m3u8'):
    """
    Grab a frame from a given video, return as buffer??
    :param path: path to folder containing .ts files
    :param start_time: start datetime of video
    :param grab_time: datetime of desired frame
    :param file: video file from which to grab frame
    :param hms: HH:mm:ss into video to grab frame
    :param index_file_name: name of the file that lists length of each .ts file
    :return:
    """
    if grab_time:
        if not start_time:
            print '**** You must specify the start time of the video ****'
            exit - 1
        time_diff = grab_time - start_time
        seconds = int(time_diff.seconds)
    elif args.hms:
        seconds = hms_to_total_s(hms)
    else:
        print '**** You must specify a time to take a frame grab ****'
        exit - 1

    if path:
        ts_file, offset = calculate_ts_file(path, seconds, index_file_name)
        # if you don't cast the offset time to an int, resulting screenshot is wavy gray
        return take_screenshot(os.path.join(path, ts_file), int(offset))
    else:
        return take_screenshot(file, seconds)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', help='path to folder containing ts files')
    parser.add_argument('-s', '--start', help='start date/time of video')
    parser.add_argument('-g', '--grab', help='date/time of desired frame')
    parser.add_argument('-o', help='prefix of output file', default='Screenshot')
    parser.add_argument('-i', '--index', help='name of index file listing ts file durations')
    parser.add_argument('-f', '--file', help='video from which to take screenshot', default='input.mov')
    parser.add_argument('-hms', help='HH:mm:ss into video to take screenshot')

    args, unknown = parser.parse_known_args()
    print args
    print unknown

    if args.grab:
        grab_time = dateparser(args.grab)
        if args.start:
            start_time = dateparser(args.start)
        else:
            # try to read from end of folder name
            tokens = args.path.split('_')
            potential_date = tokens[-1]
            # reasoning that if a valid date is in the name, it must be at least 12 char
            if len(potential_date) > 12:
                try:
                    start_time = dateparser(potential_date)
                except ValueError:
                   print '**** Unable to infer video start time from folder name ****'
                   exit - 1
            else:
                print '**** You must specify the start time of the video ****'

    img_bytes = grab_frame(args.path, start_time, grab_time, args.file, args.hms, args.index)

    outfile_name = args.o + '_' + str(grab_time.strftime("%Y.%m.%d-%H.%M.%S")) + '.png'

    with open(outfile_name, 'wb') as f:
        f.write(img_bytes)
        f.close()

