# import the necessary packages
import numpy as np
import sys
import time
import cv2
import os
import uuid
import base64
from flask import Flask, jsonify, request, render_template
import threading
from queue import Queue

app = Flask(__name__)

# construct the argument parse and parse the arguments
confthres = 0.3
nmsthres = 0.1


def get_labels(labels_path):
    # load the COCO class labels our YOLO model was trained on
    lpath = os.path.sep.join([yolo_path, labels_path])

    print(yolo_path)
    LABELS = open(lpath).read().strip().split("\n")
    return LABELS


def get_weights(weights_path):
    # derive the paths to the YOLO weights and model configuration
    weightsPath = os.path.sep.join([yolo_path, weights_path])
    return weightsPath


def get_config(config_path):
    configPath = os.path.sep.join([yolo_path, config_path])
    return configPath


def load_model(configpath, weightspath):
    # load our YOLO object detector trained on COCO dataset (80 classes)
    print("[INFO] loading YOLO from disk...")
    net = cv2.dnn.readNetFromDarknet(configpath, weightspath)
    return net


def do_prediction(image, net, LABELS):

    (H, W) = image.shape[:2]
    # determine only the *output* layer names that we need from YOLO
    ln = net.getLayerNames()
    ln = [ln[i - 1] for i in net.getUnconnectedOutLayers()]

    # construct a blob from the input image and then perform a forward
    # pass of the YOLO object detector, giving us our bounding boxes and
    # associated probabilities
    blob = cv2.dnn.blobFromImage(image, 1 / 255.0, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    start = time.time()
    layerOutputs = net.forward(ln)
    # print(layerOutputs)
    end = time.time()

    # show timing information on YOLO
    print("[INFO] YOLO took {:.6f} seconds".format(end - start))

    # initialize our lists of detected bounding boxes, confidences, and
    # class IDs, respectively
    boxes = []
    confidences = []
    classIDs = []

    # loop over each of the layer outputs
    for output in layerOutputs:
        # loop over each of the detections
        for detection in output:
            # extract the class ID and confidence (i.e., probability) of
            # the current object detection
            scores = detection[5:]
            # print(scores)
            classID = np.argmax(scores)
            # print(classID)
            confidence = scores[classID]

            # filter out weak predictions by ensuring the detected
            # probability is greater than the minimum probability
            if confidence > confthres:
                # scale the bofunding box coordinates back relative to the
                # size of the image, keeping in mind that YOLO actually
                # returns the center (x, y)-coordinates of the bounding
                # box followed by the boxes' width and height
                box = detection[0:4] * np.array([W, H, W, H])
                (centerX, centerY, width, height) = box.astype("int")

                # use the center (x, y)-coordinates to derive the top and
                # and left corner of the bounding box
                x = int(centerX - (width / 2))
                y = int(centerY - (height / 2))

                # update our list of bounding box coordinates, confidences,
                # and class IDs
                boxes.append([x, y, int(width), int(height)])

                confidences.append(float(confidence))
                classIDs.append(classID)

    # apply non-maxima suppression to suppress weak, overlapping bounding boxes
    idxs = cv2.dnn.NMSBoxes(boxes, confidences, confthres, nmsthres)

    # Prepare the output as required to the assignment specification
    # ensure at least one detection exists
    output_obj = []
    if len(idxs) > 0:
        # loop over the indexes we are keeping
        for i in idxs.flatten():
            print(
                "detected item:{}, accuracy:{}, X:{}, Y:{}, width:{}, height:{}".format(
                    LABELS[classIDs[i]],
                    confidences[i],
                    boxes[i][0],
                    boxes[i][1],
                    boxes[i][2],
                    boxes[i][3],
                )
            )
            found_obj = {
                "label": LABELS[classIDs[i]],
                "accuracy": confidences[i],
                "rectangle": {
                    "height": boxes[i][0],
                    "left": boxes[i][1],
                    "top": boxes[i][2],
                    "width": boxes[i][3],
                },
            }
            output_obj.append(found_obj)
        print(output_obj)

    client_obj = None
    if output_obj:
        client_obj = {
            "id": str(uuid.uuid4()),
            "object": output_obj,
        }
    print("client object", client_obj)
    return client_obj


yolo_path = "yolo_tiny_configs/"

## Yolov3-tiny version
labelsPath = "coco.names"
cfgpath = "yolov3-tiny.cfg"
wpath = "yolov3-tiny.weights"

labels = get_labels(labelsPath)
CFG = get_config(cfgpath)
weights = get_weights(wpath)


def main():
    try:
        imagefile = str(sys.argv[2])
        img = cv2.imread(imagefile)
        npimg = np.array(img)
        image = npimg.copy()
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # Load the neural net. Should be local to this method as its multi-threaded endpoint
        nets = load_model(CFG, weights)
        client_obj = do_prediction(image, nets, labels)
        if client_obj:
            print(client_obj)

    except Exception as e:
        print("Exception {}".format(e))


def process_image(image, nets, labels, result):
    result.update({"client_obj": do_prediction(image, nets, labels)})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    image_str = ""
    if request.method == "POST":
        if "image" in request.files:
            file = request.files["image"]
            image_data = file.read()
            image_str = base64.b64encode(image_data).decode("utf-8")

    return jsonify(
        {
            "id": str(uuid.uuid4()),
            "image": image_str,
        }
    )


@app.route("/detect", methods=["POST"])
def detect_image():
    if request.method == "POST":
        json = request.json
        client_obj = {}
        if json:
            img_object = json["image"]
            try:
                image_data = base64.b64decode(img_object)
                nparr = np.frombuffer(image_data, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                # TODO: Load the neural net. Should be local to this method as its multi-threaded endpoint
                nets = load_model(CFG, weights)

                # Create a new thread for processing the image
                thread = threading.Thread(
                    target=process_image, args=(image, nets, labels, client_obj)
                )
                thread.start()

                # Wait for the thread to complete and get the result
                thread.join()

                if json["id"]:
                    client_obj.update({"id": json["id"]})

            except Exception as e:
                print("Exception {}".format(e))
        else:
            return jsonify({"error": "There is an error on detect image"}), 400

        return jsonify(client_obj.get("client_obj"))


if __name__ == "__main__":
    if len(sys.argv) == 3:
        main()
    elif len(sys.argv) == 1:
        app.run(host="0.0.0.0", port=5000, threaded=True)
    else:
        raise ValueError(
            "Argument list is wrong. Please use the following format:  {} {} {}".format(
                "python iWebLens_server.py", "<yolo_config_folder>", "<Image file path>"
            )
        )
