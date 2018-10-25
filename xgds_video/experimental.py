#!/usr/bin/env python

import ffmpeg
import argparse
import m3u8
import os
import string

def take_screenshot(input_file, seconds_into, output_name):
    {
        ffmpeg
        .input(input_file, ss=seconds_into)
        .filter('scale', -1, -1)
        .output(output_name, vframes=1)
        .run()
    }

def calculate_ts_file(folder_name, s_int):
    # open the prog_index.m3u8
    m3u8_obj = m3u8.load(os.path.join(folder_name, 'prog_index.m3u8'))

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

    if file_number == num_segs:
        print "HOUSTON WE HAVE A PROBLEM"
        exit -1

    return m3u8_obj.segments[file_number].uri, s_float - acc_time


def hms_to_total_s(hms_string):
    tokens = hms_string.split(':')
    if(len(tokens) == 3):
        h = tokens[0]
        m = tokens[1]
        s = tokens[2]
    elif(len(tokens) == 2):
        h = 0
        m = tokens[0]
        s = tokens[1]
    elif(len(tokens) == 1):
        h = 0
        m = 0
        s = tokens[0]
    ans = int(s) + int(m)*60 + int(h)*60*60
    return ans


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', help='video from which to take screenshot', default='input.mov')
    parser.add_argument('-ts', help='name of the folder containing ts files')
    parser.add_argument('-hms', help='HH:mm:ss into video to take screenshot', default=2)
    parser.add_argument('-o', help='name of output file', default='output.png')

    args, unknown = parser.parse_known_args()
    print args
    print unknown

    seconds = hms_to_total_s(args.hms)

    if args.ts:
        ts_file, offset = calculate_ts_file(args.ts, seconds)
        print 'ASKING FOR ' + os.path.join(args.ts, ts_file) + ' AT SECOND ' + str(int(offset))
        # if you don't cast the offset time to an int picture is wavy gray
        take_screenshot(os.path.join(args.ts, ts_file), int(offset), args.o)
    else:
        take_screenshot(args.f, seconds, args.o)