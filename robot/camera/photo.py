import os
import time
import cv2 as cv
from .camera import Camera


def main():
    cam = Camera()
    cam.open()

    photos_dir = os.path.join(os.getcwd(), "photos")
    os.makedirs(photos_dir, exist_ok=True)

    ok, frame = cam.read()
    if not ok or frame is None:
        print("Failed to capture frame.")
        cam.release()
        return

    filename = time.strftime("photo-%Y%m%d-%H%M%S.jpg")
    path = os.path.join(photos_dir, filename)
    cv.imwrite(path, frame, [cv.IMWRITE_JPEG_QUALITY, 100])
    print(f"Saved: {path}")

    cam.release()


if __name__ == "__main__":
    main()