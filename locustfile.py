from locust import HttpUser, task, between
import os
import random
import base64


class MyUser(HttpUser):

    # Wait time configuration
    wait_time = between(1, 2)
    host = "http://207.211.145.31:30003"

    def get_images(self):
        current_dir = os.path.join(os.path.dirname(os.path.realpath(__name__)), "images/")
    
        return [os.path.join(current_dir, image_path) \
                for image_path in os.listdir(current_dir)]

    @task
    def detect_image(self):
        """
            Accept json image string only
        """
        images_list = self.get_images()
        chosen_image_path = random.choice(images_list)
        chosen_image = open(chosen_image_path, "rb").read()
        payload = {}
        if chosen_image:
            encode_image = base64.b64encode(chosen_image).decode('utf-8')

            payload = {
                "id": "",
                "image": encode_image
            }
        
        upload_response = self.client.post("/upload", files=payload)
        if upload_response.status_code == 200:
            image_json = upload_response.json()
            self.client.post("/detect", json=image_json)

    @task    
    def detect_all_images(self):
        """
            Accept json image string only
        """
        images_list = self.get_images()
        for image_path in images_list:
            image_obj = open(image_path, "rb").read()
            if image_obj:
                encode_image = base64.b64encode(image_obj).decode('utf-8')

                payload = {
                    "id": "",
                    "image": encode_image
                }

            upload_response = self.client.post("/upload", files=payload)
            if upload_response.status_code == 200:
                image_json = upload_response.json()
                self.client.post("/detect", json=image_json)
