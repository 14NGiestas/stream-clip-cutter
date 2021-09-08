import cv2 
import ffmpeg
import tempfile
from argparse import ArgumentParser

WEBCAM_WINDOW = "Select the webcam feed"
GAMEFEED_WINDOW = "Select the gamefeed"

def width_concatenate(image_list, resize_to=min, interpolation=cv2.INTER_CUBIC):
    width = resize_to(image.shape[1] for image in image_list)
    resize_width = lambda image: (width, int(image.shape[0] * width / image.shape[1]))
    image_list = [cv2.resize(image, resize_width(image), 
                      interpolation=interpolation)
                      for image in image_list]
    return cv2.vconcat(image_list)


def select_roi(window_name, frame):
    def on_mouse(event, x, y, flags, selection):
        if event == cv2.EVENT_LBUTTONDOWN:
            selection.start = (x,y)
            selection.coords = (0,0,0,0)
        elif event == cv2.EVENT_LBUTTONUP:
            selection.start = None
        elif selection.start:
            if flags & cv2.EVENT_FLAG_LBUTTON:
                minpos = min(selection.start[0], x), min(selection.start[1], y)
                maxpos = max(selection.start[0], x), max(selection.start[1], y)
                x1,y1,x2,y2 = selection.coords = minpos[0], minpos[1], maxpos[0], maxpos[1]
                img = frame.copy()
                cv2.rectangle(img, (x1, y1), (x2, y2), (0,255,255), 1)
                cv2.imshow(window_name, img)
            else:
                print("selection is complete")
                selection.start = None

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    class selection:
        start = None
        coords = (0,0,0,0)

    cv2.setMouseCallback(window_name, on_mouse, selection)

    cv2.imshow(window_name, frame)
    while True:
        k = cv2.waitKey(0)
        if k == ord('q'):
            exit()
        elif k == 13: # Enter
            cv2.destroyAllWindows()
            x1,y1,x2,y2 = selection.coords
            x = y1
            y = x1
            w = abs(y1-y2)
            h = abs(x1-x2)
            return (x,y,w,h)

def main():
    resolution_to_tuple = lambda string: tuple(map(int,string.split('x')))
    parser = ArgumentParser(prog='streamcut')
    parser.add_argument('input', help='The source video')
    parser.add_argument('output', help='The output video')
    parser.add_argument('-s', '--aspect', type=lambda s: resolution_to_tuple(s), default=resolution_to_tuple('720x1280'))
    args = parser.parse_args()
    video = cv2.VideoCapture(args.input)
    num_frames = video.get(cv2.CAP_PROP_FRAME_COUNT)
    video_fps = video.get(cv2.CAP_PROP_FPS)

    with tempfile.NamedTemporaryFile(suffix='.mp4') as f: 
        output = cv2.VideoWriter(f.name, cv2.VideoWriter_fourcc('M','J','P','G'), video_fps, args.aspect)

        info, frame = video.read()
        webcam_roi   = select_roi(WEBCAM_WINDOW,   frame)
        print(webcam_roi)
        gamefeed_roi = select_roi(GAMEFEED_WINDOW, frame)
        print(gamefeed_roi)

        while video.isOpened(): 
            info, frame = video.read()
            if not info: break
            (x,y,w,h) = webcam_roi
            webcam   = frame[x:x+w,y:y+h]
            (x,y,w,h) = gamefeed_roi
            gamefeed = frame[x:x+w,y:y+h]
            concat = width_concatenate([webcam, gamefeed])
            final = cv2.resize(concat, args.aspect, interpolation=cv2.INTER_CUBIC)
            output.write(final)
        output.release()
        original = ffmpeg.input(args.input)
        no_sound = ffmpeg.input(f.name)
        out = ffmpeg.output(original.audio, no_sound, args.output) 
        out.run()
   

if __name__ == '__main__':
    main()
