import cv2
import numpy as np
from PIL import Image

def get_auto_bounding_box(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Threshold to find light areas (like white T-shirts or blank spaces)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    # Find contours in the thresholded image
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        # Sort by largest contour area
        largest_contour = sorted(contours, key=cv2.contourArea, reverse=True)[0]
        x, y, w, h = cv2.boundingRect(largest_contour)

        # Return bounding box
        return (x, y, x + w, y + h)

    # Fallback to center box
    height, width = gray.shape
    return (width//3, height//3, width//3*2, height//3*2)
