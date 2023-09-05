import os
import time

import torch
import cv2
from torchvision import transforms
import numpy as np
from PIL import Image

from src import UNet


def time_synchronized():
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    return time.time()


def main():
    classes = 1  # exclude background
    weights_path = "./save_weights/model_best.pth"
    img_path = "data/TP-Dataset/JPEGImages"
    txt_path = "data/TP-Dataset/ImageSets/Segmentation/predict.txt"
    save_weights = "./predict"

    assert os.path.exists(weights_path), f"weights {weights_path} not found."
    assert os.path.exists(img_path), f"image {img_path} not found."


    mean = (0.709, 0.381, 0.224)
    std = (0.127, 0.079, 0.043)

    # get devices
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print("using {} device.".format(device))

    # create model
    model = UNet(in_channels=3, num_classes=classes+1, base_c=32)

    # load weights
    model.load_state_dict(torch.load(weights_path, map_location='cpu')['model'])
    model.to(device)


    total_time = 0
    with open(os.path.join(txt_path), 'r') as f:
        file_name = [x.strip() for x in f.readlines() if len(x.strip()) > 0]
    for file in file_name:
      original_img = Image.open(os.path.join(img_path, file + ".jpg"))

      h = np.array(original_img).shape[0]
      w = np.array(original_img).shape[1]



      data_transform = transforms.Compose([transforms.Resize(565),
                                         transforms.ToTensor(),
                                         transforms.Normalize(mean=mean, std=std)])
      img = data_transform(original_img)
      # expand batch dimension

      img = torch.unsqueeze(img, dim=0)

      model.eval()  # Entering Validation Mode
      with torch.no_grad():
        # init model
        img_height, img_width = img.shape[-2:]
        init_img = torch.zeros((1, 3, img_height, img_width), device=device)
        model(init_img)

        t_start = time_synchronized()
        output = model(img.to(device))
        t_end = time_synchronized()
        total_time = total_time + (t_end - t_start)
        print("inference+NMS time: {}".format(t_end - t_start))

        prediction = output['out'].argmax(1).squeeze(0)
        prediction = prediction.to("cpu").numpy().astype(np.uint8)
        prediction = cv2.resize(prediction, (w, h), interpolation = cv2.INTER_LINEAR)
        # Change the pixel value corresponding to the foreground to 255 (white)
        prediction[prediction == 1] = 255
        # Set the pixels in the area of no interest to 0 (black)
        prediction[prediction == 0] = 0
        mask = Image.fromarray(prediction)
        mask = mask.convert("L")
        name = file[0:4]

        mask.save(os.path.join(save_weights, f'{name}.png'))
    fps = 1 / (total_time / 286)
    print("FPS: {}".format(fps))


if __name__ == '__main__':
    main()