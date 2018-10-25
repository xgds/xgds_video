#!/usr/bin/env python

import ffmpeg
import argparse
import m3u8
import os

def take_screenshot(input_file, seconds_into, output_name):
    {
        ffmpeg
        .input(input_file, ss=seconds_into)
        .filter('scale', -1, -1)
        .output(output_name, vframes=1)
        .run()
    }

def screenshotify(input_file, max_seconds, out_folder):
    for s in range(1,max_seconds):
        next_string = os.path.join(out_folder, "out" + str(s) + ".png")
        take_screenshot(input_file, s, next_string)
    
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
            # save previous file number
            file_number = seg_num - 1
            break

        acc_time = acc_time + next_delta

    return m3u8_obj.segments[seg_num].uri, s_float - acc_time


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', help='video from which to take screenshot(s)', default='input.mov')
    parser.add_argument('-ts', help='name of the folder containing ts files')
    parser.add_argument('-ss', help='=s into video to take screenshot, or (many) stop taking screenshots', default='100')
    parser.add_argument('-o', help='name of output file or (many) folder', default='output.png')
    parser.add_argument('-many', help='take screenshots from 0 to ss seconds', action="store_true")

    args, unknown = parser.parse_known_args()
    print args
    print unknown

    if args.ts:
        ts_file, offset = calculate_ts_file(args.ts, args.ss)
        print 'ASKING FOR ' + os.path.join(args.ts, ts_file) + ' AT SECOND ' + str(int(offset))
        take_screenshot(os.path.join(args.ts, ts_file), int(offset), args.o)
    elif args.many:
        screenshotify(args.f, int(args.ss), args.o)
    else:
        take_screenshot(args.f, args.ss, args.o)