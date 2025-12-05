from flask import Flask, render_template, send_from_directory, redirect, url_for, request, Response
from gpiozero import LED, Button, MotionSensor
import cv2
import os
import time
from datetime import datetime

app = Flask(__name__)

SAVE_DIR = "pictures"
os.makedirs(SAVE_DIR, exist_ok=True)

#Глобални променливи за камерата, led, бутон и PIR-сензор
camera = None
led = LED(17)
button = Button(27, pull_up=True)
pir = MotionSensor(22)


def get_camera():
    """Връща отворена камера, ако трябва – я отваря."""
    global camera

    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(0, cv2.CAP_V4L2)

        if not camera.isOpened():
            print("[ERROR] Не мога да отворя камерата на индекс 0")
            return None
    return camera


def get_frame():
    """Взима един кадър от общата камера."""
    cam = get_camera()
    if cam is None:
        return None

    ret, frame = cam.read()
    if not ret:
        print("[ERROR] Неуспешно четене от камерата")
        return None

    return frame


def take_picture():
    """Прави снимка, без да отваря нова VideoCapture."""
    frame = get_frame()
    if frame is None:
        return None

    filename = datetime.now().strftime("img_%Y%m%d_%H%M%S.jpg")
    filepath = os.path.join(SAVE_DIR, filename)
    cv2.imwrite(filepath, frame)
    return filename


def handle_event(source):
    print(f"Събитие от: {source}")
    led.on()
    filename = take_picture()
    print("Направена снимка:", filename)
    time.sleep(0.5)
    led.off()


def generate_frames():
    """MJPEG стрийм, използващ същата камера."""
    fail_count = 0

    while True:
        frame = get_frame()

        if frame is None:
            fail_count += 1
            if fail_count >= 10:
                # опит за reset на камерата
                global camera
                if camera is not None:
                    camera.release()
                    camera = None
                fail_count = 0
                print("[WARN] Рестартирам камерата...")
            time.sleep(0.1)
            continue

        fail_count = 0

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            time.sleep(0.02)
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
        )

        # ограничаваме се примерно до ~25 fps
        time.sleep(0.04)



@app.route("/")
def index():
    images = []
    if os.path.exists(SAVE_DIR):
        images = sorted(os.listdir(SAVE_DIR), reverse=True)

    return render_template("index.html", images=images)


@app.route("/gallery")
def gallery():
    images = []
    if os.path.exists(SAVE_DIR):
        images = sorted(os.listdir(SAVE_DIR), reverse=True)

    return render_template("gallery.html", images=images)


@app.route("/preview/<filename>")
def preview(filename):
    next_page = request.args.get("next", "/")
    return render_template("preview.html", filename=filename, next_page=next_page)


@app.route("/snapshot")
def snapshot():
    filename = take_picture()
    if filename is None:
        return "Грешка при снимане :(", 500

    return redirect(url_for("preview", filename=filename, next="/"))


@app.route("/pictures/<filename>")
def pictures(filename):
    return send_from_directory(SAVE_DIR, filename)


@app.route("/delete/<filename>", methods=["POST"])
def delete_image(filename):
    safe_name = os.path.basename(filename)
    path = os.path.join(SAVE_DIR, safe_name)

    if os.path.exists(path):
        os.remove(path)
        print("Изтрита снимка:", path)
    else:
        print("Опит за триене на несъществуващ файл:", path)

    return redirect(request.referrer or url_for("index"))


@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/live")
def live():
    return render_template("live.html")


@app.route("/live_snapshot")
def live_snapshot():
    filename = take_picture()
    if filename is None:
        return "Грешка при снимане", 500

    return redirect(url_for("preview", filename=filename, next="/live"))

button.when_pressed = lambda: handle_event("бутон")
pir.when_motion = lambda: handle_event("PIR")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
