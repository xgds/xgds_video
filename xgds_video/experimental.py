#!/usr/bin/env python

import ffmpeg
import argparse
import m3u8

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
        next_string = out_folder + "/out" + str(s) + ".png"
        take_screenshot(input_file, s, next_string)
    

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', help='video from which to take screenshot(s)', default='input.mov')
    parser.add_argument('-ss', help='=s into video to take screenshot, or (many) stop taking screenshots', default='100')
    parser.add_argument('-o', help='name of output file or (many) folder', default='output.png')
    parser.add_argument('-many', help='take screenshots from 0 to ss seconds', action="store_true")

    args, unknown = parser.parse_known_args()
    print args
    print unknown

    if args.many:
        screenshotify(args.f, int(args.ss), args.o)
    else:
        take_screenshot(args.f, args.ss, args.o)