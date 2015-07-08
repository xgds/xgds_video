#import <Foundation/Foundation.h>
#import <AVFoundation/AVFoundation.h>
#import <CoreMedia/CoreMedia.h>
#import <czmq.h>

// The settings below can be overridden with command line options zmqPort and zmqIP respectively.
#define DEFAULT_ZMQ_PORT 6666
#define DEFAULT_ZMQ_IP @"0.0.0.0"

typedef struct _frameParams {
  NSString *chunkFilePath;
  double frameCaptureOffset;
  NSString *imageSubject;
  NSDate *wallClockTime;
  NSDictionary *locationInfo;
  NSString *contactInfo;
  BOOL createThumbnail;
  NSSize thumbnailSize;
  NSString *outputDir;
  NSString *collectionTimeZoneName;
} frameParams;

// ---------------------------------------------------------------------------
//		printNSString
// ---------------------------------------------------------------------------
static void printNSString(NSString *string)
{
	printf("%s\n", [string cStringUsingEncoding:NSUTF8StringEncoding]);
}

// ---------------------------------------------------------------------------
// Input: A JSON dictionary via ZeroMQ message with the following fields:
//   chunkFilePath: absolute path (on server side) to HLS chunk with the 
//                  frame to be captured.  Asssumption is a common file system
//                  (e.g. NFS) between server and client machnines.
//   frameCaptureOffset: time (within chunk) to grab a frame. Float in seconds
//                     with fractional part allowed and respected.
//   imageSubject: Optional additional info to store in IPTCSubjectReference
//                 metadata field.  Good place to put PLRP flight #.
//   wallClockTime: A Unix timestamp (seconds since 1/1/1970) of the time
//                  when the frame was captured.  Used for image metadata.
//   locationInfo: A json dict with "latitude", "longitude" and "altitude" tags showing where 
//                 frame was grabbed.  May be omitted if location not availble.
//   contactInfo: A string with contact info for the image (e.g. web site URL or email)
//   createThumbnail: True or false to indicate if thumbnail image should be 
//                   created.  Typically used for console log notes.
//   thumbnailSize: JSON dict with "width" and "height" tags.
//   outputDir: Directory to write the captured frame and thumbnail, if
//              requested.  Thumbnail will be named <basename>.thumb.jpg
//              
// Output: A JSON dictionary with the following fields:
//   captureSuccess: true if frame capture and save to file(s) succeeded.
//   imageUuid: UUID used as filename and also stored IPTCObjectName field.
// ---------------------------------------------------------------------------

NSDictionary *buildGPSMetadata(NSDictionary *locationInfo) {
  double lat = [[locationInfo objectForKey:@"latitude"] doubleValue];
  double lon = [[locationInfo objectForKey:@"longitude"] doubleValue];
  double altitude = fabs([[locationInfo objectForKey:@"altitude"] doubleValue]);
  NSString *nsHemi = (lat > 0.0) ? @"N" : @"S";
  NSString *ewHemi = (lon > 0.0) ? @"E" : @"W";
  lat = fabs(lat);
  lon = fabs(lon);

  NSDictionary* gpsInfo =
    [NSDictionary dictionaryWithObjects:
		     [NSArray arrayWithObjects:[NSNumber numberWithDouble:lat],
			      nsHemi, [NSNumber numberWithDouble:lon], ewHemi,
			      [NSNumber numberWithDouble:altitude], @"A-OK", nil]
			 forKeys:[NSArray 
				   arrayWithObjects:(id)kCGImagePropertyGPSLatitude,
				   kCGImagePropertyGPSLatitudeRef,
				   kCGImagePropertyGPSLongitude,
				   kCGImagePropertyGPSLongitudeRef,
				   kCGImagePropertyGPSAltitude,
				   kCGImagePropertyGPSStatus, nil]];
  return gpsInfo;
}

NSDictionary *createImageMetadata(CGImageRef image, NSString *imageUuid, frameParams params) {
  CGDataProviderRef provider = CGImageGetDataProvider(image);
  CGImageSourceRef imgSource = CGImageSourceCreateWithDataProvider(provider, NULL);

  // Get any metadata currently attached to image
  NSDictionary* props = (NSDictionary*) CGImageSourceCopyPropertiesAtIndex(imgSource, 0, NULL);
  NSMutableDictionary* propsW = [NSMutableDictionary dictionaryWithDictionary:props];

  // Now start adding new items passed in params argument
  if (params.locationInfo)
    [propsW setValue:buildGPSMetadata(params.locationInfo) forKey:(id)kCGImagePropertyGPSDictionary];

  NSDateFormatter *dateFormatter = [[NSDateFormatter alloc] init];
  NSDateFormatter *timeFormatter = [[NSDateFormatter alloc] init];
  [dateFormatter setDateFormat:@"yyyMMdd"];
  [timeFormatter setDateFormat:@"HHmmss"];

  // Capture (digitization) time is in server timezone, for now
  NSDate *digitizedTimestamp = [NSDate date];
  NSString *timeDigitizedString = [timeFormatter stringFromDate:digitizedTimestamp];
  NSString *dateDigitizedString = [dateFormatter stringFromDate:digitizedTimestamp];
  NSString *digitizedTimeZoneName = [[timeFormatter timeZone] name];
  NSString *collectionTimeZoneName = digitizedTimeZoneName;

  // If we're given a different timezone for the original video, we use it here
  if (params.collectionTimeZoneName) {
    [timeFormatter setTimeZone:[NSTimeZone timeZoneWithName:params.collectionTimeZoneName]];
    [dateFormatter setTimeZone:[NSTimeZone timeZoneWithName:params.collectionTimeZoneName]];
    collectionTimeZoneName = params.collectionTimeZoneName;
  }
  NSString *timeCreatedString = [timeFormatter stringFromDate:params.wallClockTime];
  NSString *dateCreatedString = [dateFormatter stringFromDate:params.wallClockTime];
  NSString *timeZoneInfo = [NSString stringWithFormat:@"Ops: %1@ -- Capture: %1@",
				     collectionTimeZoneName, digitizedTimeZoneName];

  NSDictionary *iptcDict = [NSDictionary dictionaryWithObjects:
					   [NSArray arrayWithObjects:params.imageSubject,
						    imageUuid,
						    dateCreatedString,
						    timeCreatedString,
						    dateDigitizedString,
						    timeDigitizedString,
						    timeZoneInfo,
						    params.contactInfo, nil]
					 forKeys:
					   [NSArray arrayWithObjects:
						      (id)kCGImagePropertyIPTCSource,
						    kCGImagePropertyIPTCObjectName,
						    kCGImagePropertyIPTCDateCreated,
						    kCGImagePropertyIPTCTimeCreated,
						    kCGImagePropertyIPTCDigitalCreationDate,
						    kCGImagePropertyIPTCDigitalCreationTime,
						    kCGImagePropertyIPTCSpecialInstructions,
						    kCGImagePropertyIPTCCredit, nil]];
  [propsW setValue:iptcDict forKey:(id)kCGImagePropertyIPTCDictionary];

  return propsW;
}

NSDictionary *captureImageFromVideo(frameParams params) {
  NSURL *chunkFileUrl = [NSURL fileURLWithPath:params.chunkFilePath];
  NSDictionary *options = 
    @{ AVURLAssetPreferPreciseDurationAndTimingKey : @YES };

  AVURLAsset *myAsset = [[AVURLAsset alloc] initWithURL:chunkFileUrl options:options];

  CMTime extractTime = CMTimeMake((int)(30.0*params.frameCaptureOffset), 30);
  AVAssetImageGenerator *imageGenerator = 
    [AVAssetImageGenerator assetImageGeneratorWithAsset:myAsset];
  CGImageRef image = [imageGenerator copyCGImageAtTime:extractTime actualTime:NULL
				     error:NULL];
  if (!image) {
    NSDictionary *resultDict = [NSDictionary dictionaryWithObjects:[NSArray arrayWithObjects:[NSNumber numberWithInteger:0], @"", nil]
					     forKeys:[NSArray arrayWithObjects:@"captureSuccess", @"imageUuid", nil]];
    return resultDict;
  }

  NSString *outputFileUuid = [[NSUUID UUID] UUIDString];
  //  NSString *outputPath = [NSString stringWithFormat:@"%@/%@.jpg", params.outputDir, outputFileUuid];
  NSDateFormatter *dateFormatter = [[NSDateFormatter alloc] init];
  [dateFormatter setDateFormat:@"yyy-MM-dd_HH-mm-ss"];
  [dateFormatter setTimeZone:[NSTimeZone timeZoneWithName:@"UTC"]];
  NSString *outputPath = [NSString stringWithFormat:@"%@/%@_%@.jpg", params.outputDir, params.imageSubject, 
				   [dateFormatter stringFromDate:params.wallClockTime]];
  NSURL *outputUrl = [NSURL fileURLWithPath:outputPath isDirectory:NO];
  NSDictionary *imageMetadata = createImageMetadata(image, outputFileUuid, params);

  CGImageDestinationRef outImgRef =
    CGImageDestinationCreateWithURL ((CFURLRef)outputUrl, kUTTypeJPEG, 1, NULL);
  CGImageDestinationAddImage(outImgRef, image, (CFDictionaryRef)imageMetadata);
  bool res = CGImageDestinationFinalize(outImgRef);
  if (res)
    printf("Image written OK!\n");
  else
    printf("Problem writing output image!!\n");

  if (params.createThumbnail) {
    double thumbnailMaxDimension = fmax(params.thumbnailSize.width, params.thumbnailSize.height);
    NSDictionary *thumbOptions = [NSDictionary dictionaryWithObjects:[NSArray arrayWithObjects:[NSNumber numberWithDouble:thumbnailMaxDimension],
									      @(YES), @(YES), nil]
					       forKeys:[NSArray arrayWithObjects:(id)kCGImageSourceThumbnailMaxPixelSize, 
								kCGImageSourceShouldAllowFloat,
								kCGImageSourceCreateThumbnailFromImageAlways, nil]];
    CGImageSourceRef imgSource = CGImageSourceCreateWithURL((CFURLRef)outputUrl, NULL);
    NSDictionary* props = (NSDictionary*) CGImageSourceCopyPropertiesAtIndex(imgSource, 0, NULL);
    CGImageRef thumbImage = CGImageSourceCreateThumbnailAtIndex(imgSource, 0, (CFDictionaryRef)thumbOptions);
    NSString *thumbPath = [NSString stringWithFormat:@"%@/%@_%@.thumbnail.jpg", params.outputDir, params.imageSubject, 
				     [dateFormatter stringFromDate:params.wallClockTime]];
    NSURL *thumbUrl = [NSURL fileURLWithPath:thumbPath isDirectory:NO];
    CGImageDestinationRef thumbDestRef =
      CGImageDestinationCreateWithURL ((CFURLRef)thumbUrl, kUTTypeJPEG, 1, NULL);
    CGImageDestinationAddImage(thumbDestRef, thumbImage, (CFDictionaryRef)imageMetadata);
    bool thumbRes = CGImageDestinationFinalize(thumbDestRef);
    if (thumbRes)
      printf("Thumbnail created OK!\n");
    else
      printf("Thumbnail creation failed!\n");

    [myAsset release];
    //    [imageGenerator release];
     CGImageRelease(image);
     CFRelease(outImgRef);
     CFRelease(imgSource);
     CGImageRelease(thumbImage);
     CFRelease(thumbDestRef);
  }

  NSDictionary *resultDict = [NSDictionary dictionaryWithObjects:[NSArray arrayWithObjects:[NSNumber numberWithInteger:res], outputFileUuid, nil]
					   forKeys:[NSArray arrayWithObjects:@"captureSuccess", @"imageUuid", nil]];
  return resultDict;
}

frameParams buildParamStructFromRequest(NSDictionary *requestParams) {
  frameParams params;
  
  params.chunkFilePath = [requestParams valueForKey:@"chunkFilePath"];
  params.frameCaptureOffset = [[requestParams valueForKey:@"frameCaptureOffset"] doubleValue];
  params.imageSubject = [requestParams valueForKey:@"imageSubject"];
  params.wallClockTime = [NSDate dateWithTimeIntervalSince1970:[[requestParams valueForKey:@"wallClockTime"] doubleValue]];
  params.locationInfo = [requestParams valueForKey:@"locationInfo"];
  params.contactInfo = [requestParams valueForKey:@"contactInfo"];
  params.createThumbnail = [[requestParams valueForKey:@"createThumbnail"] boolValue];
  NSDictionary *thumbnailDict = [requestParams valueForKey:@"thumbnailSize"];
  params.thumbnailSize = (NSSize){[[thumbnailDict valueForKey:@"width"] doubleValue], [[thumbnailDict valueForKey:@"height"] doubleValue]};
  params.outputDir = [requestParams valueForKey:@"outputDir"];
  params.collectionTimeZoneName = [requestParams valueForKey:@"collectionTimeZoneName"];

  return params;
}

int main(int argc, char *argv[]) {
  @autoreleasepool {
  NSUserDefaults *defaults = [NSUserDefaults standardUserDefaults];
  [defaults registerDefaults:[NSDictionary dictionaryWithObjects:[NSArray arrayWithObjects:[NSNumber numberWithInteger:DEFAULT_ZMQ_PORT],
									  DEFAULT_ZMQ_IP, nil]
					   forKeys:[NSArray arrayWithObjects:@"zmqPort", @"zmqIP", nil]]];

  // Create ZMQ server socket with requested settings
  NSString *zmqEndpoint = [NSString stringWithFormat:@"tcp://%@:%1ld", [defaults stringForKey:@"zmqIP"], [defaults integerForKey:@"zmqPort"]];
  printf("Creating ZMQ socket at endpoint: %s\n", [zmqEndpoint UTF8String]);
  zsock_t *serverSocket = zsock_new_rep([zmqEndpoint UTF8String]);

  char keepGoing = YES;

  while(keepGoing) {
    @autoreleasepool {

    char *requestMsgCstr = zstr_recv(serverSocket);
    NSString *requestMsg = [NSString stringWithCString:requestMsgCstr encoding:NSASCIIStringEncoding];
    zstr_free(&requestMsgCstr);
    printf("Received ZMQ string: %s\n", [requestMsg UTF8String]);
    if ([requestMsg isEqualToString:@"<quit>"]) {
      keepGoing = NO;
      break;
    }

    NSDictionary *requestParams = [NSJSONSerialization JSONObjectWithData:[requestMsg dataUsingEncoding:NSUTF8StringEncoding]
						       options:0 error:NULL];
    frameParams params = buildParamStructFromRequest(requestParams);
    NSDictionary *response = captureImageFromVideo(params);

    NSData *responseData = [NSJSONSerialization dataWithJSONObject:response options:0 error:NULL];
    NSString *responseString = [[NSString alloc] initWithData:responseData encoding:NSASCIIStringEncoding];
    zstr_send(serverSocket, [responseString UTF8String]);

    }
  }

  zsock_destroy(&serverSocket);
  }
  exit(1);
}

// Local Variables:
// compile-command: "cc -o HLSFrameGrab HLSFrameGrab.m -I/usr/local/include -L/usr/local/lib -framework AVFoundation \
// -framework CoreMedia -framework Foundation -framework ImageIO -framework ApplicationServices \
// -framework CoreServices -lczmq" */
// End:

// [NSDictionary dictionaryWithObjects:[NSArray arrayWithObjects:@(YES), [[NSUUID UUID] UUIDString], nil]
//					   forKeys:[NSArray arrayWithObjects:@"captureSuccess", @"imageUuid", nil]];
