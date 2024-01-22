#!/usr/bin/env python

import io
import logging
import os
import socketserver
from http import server
from threading import Condition

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from PIL import Image

import time
import cv2
import face_recognition
import numpy as np

DEBUG = False # More verbose debug
picamera = True # USE PICAMERA?

# HTML page for the MJPEG streaming demo
PAGE = """\
<html>
<head>
<title>WOC</title>
</head>
<body>
<h1>Big WOC is watching you</h1>
<img src="stream.mjpg" width="640" height="480" />
</body>
</html>
"""

# Load sample pictures and learn how to recognize them.
obama_image = face_recognition.load_image_file("./faces/obama.jpg")
obama_face_encoding = face_recognition.face_encodings(obama_image)[0]

biden_image = face_recognition.load_image_file("./faces/biden.jpg")
biden_face_encoding = face_recognition.face_encodings(biden_image)[0]

#nel_image = face_recognition.load_image_file("./faces/nel.jpg")
#nel_face_encoding = face_recognition.face_encodings(nel_image)[0]

#ek_image = face_recognition.load_image_file("./faces/ek.jpg")
#ek_face_encoding = face_recognition.face_encodings(ek_image)[0]

me_image = face_recognition.load_image_file("./faces/me.jpg")
me_face_encoding = face_recognition.face_encodings(me_image)[0]

# Create arrays of known face encodings and their names
known_face_encodings = [
    obama_face_encoding,
    biden_face_encoding,
    #nel_face_encoding,
    #ek_face_encoding,
    me_face_encoding,
]
known_face_names = [
    "Barack Obama",
    "Joe Biden",
    #"Nelson Kanda",
    #"Alex El-Khoury",
    "Haydon Behl",
]

# Class to handle streaming output
class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

# Class to handle HTTP requests
class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # Redirect root path to index.html
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            # Serve the HTML page
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            # Set up MJPEG streaming
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                startTime = time.time()
                spf = 1./30.
                while True:
                    time.sleep(0.005)
                    if time.time() - startTime < spf: continue
                    startTime = time.time()

                    if picamera: frame = picam2.capture_array("main")
                    else: ret, frame = video_capture.read()

                    frame = np.ascontiguousarray(frame)
                    if DEBUG:
                        print("SHAPE: ", end="")
                        print(frame.shape)

                    # Resize frame of video to 1/4 size for faster face recognition processing
                    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

                    # Find all the faces and face encodings in the current frame of video
                    face_locations = face_recognition.face_locations(small_frame)
                    face_encodings = face_recognition.face_encodings(small_frame, face_locations)

                    face_names = []
                    for face_encoding in face_encodings:
                        # See if the face is a match for the known face(s)
                        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                        name = "Unknown"

                        # # If a match was found in known_face_encodings, just use the first one.
                        # if True in matches:
                        #     first_match_index = matches.index(True)
                        #     name = known_face_names[first_match_index]

                        # Or instead, use the known face with the smallest distance to the new face
                        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            name = known_face_names[best_match_index]

                        face_names.append(name)

                    # Display the results
                    for (top, right, bottom, left), name in zip(face_locations, face_names):
                        # Scale back up face locations since the frame we detected in was scaled to 1/4 size
                        top *= 4
                        right *= 4
                        bottom *= 4
                        left *= 4

                        # Draw a box around the face
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

                        # Draw a label with a name below the face
                        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                        font = cv2.FONT_HERSHEY_DUPLEX
                        cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

                    # Display the resulting image
                    image = Image.fromarray(frame.astype('uint8')).convert('RGB')
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='jpeg')
                    img_byte_arr = img_byte_arr.getvalue()
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(img_byte_arr))
                    self.end_headers()
                    self.wfile.write(img_byte_arr)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            # Handle 404 Not Found
            self.send_error(404)
            self.end_headers()

# Class to handle streaming server
class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

if picamera:        # Create Picamera2 instance and configure it
    picam2 = Picamera2()
    mode = picam2.sensor_modes[3] #prevents the pi5 from being stupid
    # 0 is green
    # 1 is blueish and yellow monitor
    # 2 is 1 but zoomed in
    # 3 just is 1
    picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
    picam2.configure(picam2.create_preview_configuration({'format': 'RGB888'}, sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']}))
    picam2.awb_mode = 'incandescent'
    output = StreamingOutput()
    picam2.start_recording(JpegEncoder(), FileOutput(output))
else: video_capture = cv2.VideoCapture(0)       # Get a reference to webcam #0 (the default one)
time.sleep(2)

try:
    # Set up and start the streaming server
    address = ('', 8000)
    server = StreamingServer(address, StreamingHandler)
    print("Serving.")
    server.serve_forever()
finally:
    # Stop recording when the script is interrupted
    if picamera: picam2.stop_recording()
    else: video_capture.release()
    cv2.destroyAllWindows()
    print("Done!")