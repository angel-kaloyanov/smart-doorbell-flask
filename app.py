from flask import Flask, render_template, send_from_directory, redirect, url_for, request, Response
import cv2
import os
from datetime import datetime

app = Flask(__name__)

SAVE_DIR = "pictures"
os.makedirs(SAVE_DIR, exist_ok=True)

# 🔹 Глобална променлива за камерата (лениво отваряне)
camera = None


def get_camera():
    """Връща отворена камера, ако трябва – я отваря."""
    global camera

    if camera is None or not camera.isOpened():
        # тук е мястото, ако искаш да смениш индекса (0 -> 1 и т.н.)
        camera = cv2.VideoCapture(0)

        # по желание – намали резолюцията
        # camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        # camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

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


def generate_frames():
    """MJPEG стрийм, използващ същата камера."""
    while True:
        frame = get_frame()
        if frame is None:
            break

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
        )


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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
