from locust import HttpUser, task, between
import os
import random
import base64


class MyUser(HttpUser):

    # Wait time configuration
    wait_time = between(1, 2)
    image_dir_path = os.path.expanduser('~')
    host = "http://localhost:5000"

    def get_images(self):
        return [os.path.join(self.image_dir_path, image_path) \
                for image_path in os.listdir(self.image_dir_path)]

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
        for image in images_list:
            image_obj = open(image, "rb").read()
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
