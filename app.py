from flask import Flask, render_template, send_from_directory, redirect, url_for, request, Response
import cv2
import os
from datetime import datetime

app = Flask(__name__)

SAVE_DIR = "pictures"
os.makedirs(SAVE_DIR, exist_ok=True)

# 🔹 ЕДНА обща камера за всичко – стрийм + снимки
camera = cv2.VideoCapture(0)


def get_frame():
    """Взима един кадър от камерата."""
    global camera

    # ако по някаква причина е затворена – отваряме пак
    if not camera.isOpened():
        camera.open(0)

    ret, frame = camera.read()
    if not ret:
        return None

    return frame


def take_picture():
    """Прави снимка, използвайки същата камера като стрийма."""
    frame = get_frame()
    if frame is None:
        return None

    filename = datetime.now().strftime("img_%Y%m%d_%H%M%S.jpg")
    filepath = os.path.join(SAVE_DIR, filename)
    cv2.imwrite(filepath, frame)
    return filename


def generate_frames():
    """MJPEG стрийм от същата камера."""
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



if __name__ == "__main__": app.run(debug=True)
