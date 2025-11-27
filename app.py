from flask import Flask, render_template, send_from_directory, redirect, url_for, request, Response
import cv2
import os
from datetime import datetime

app = Flask(__name__)

SAVE_DIR = "pictures"
os.makedirs(SAVE_DIR, exist_ok=True)


def take_picture():
    cap = cv2.VideoCapture(0)  # камерата (USB / лаптоп / Raspberry)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        return None

    filename = datetime.now().strftime("img_%Y%m%d_%H%M%S.jpg")
    filepath = os.path.join(SAVE_DIR, filename)
    cv2.imwrite(filepath, frame)
    return filename


def generate_frames():
    cap = cv2.VideoCapture(0)  # USB камерата
    # По желание – намали резолюцията за по-малко натоварване:
    # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while True:
        success, frame = cap.read()
        if not success:
            break

        # Преобразуваме кадъра в JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        # Връщаме го като част от MJPEG stream
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
        )

    cap.release()


@app.route("/")
def index():
    images = []
    if os.path.exists(SAVE_DIR):
        images = sorted(os.listdir(SAVE_DIR), reverse=True)  # най-новите отпред

    return render_template("index.html", images=images)


@app.route("/gallery")
def gallery():
    images = []
    if os.path.exists(SAVE_DIR):
        images = sorted(os.listdir(SAVE_DIR), reverse=True)

    return render_template("gallery.html", images=images)


@app.route("/preview/<filename>")
def preview(filename):
    # Страница за преглед на конкретна снимка
    return render_template("preview.html", filename=filename)


@app.route("/snapshot")
def snapshot():
    filename = take_picture()
    if filename is None:
        return "Грешка при снимане :(", 500

    # пренасочваме към preview страницата
    return redirect(url_for("preview", filename=filename))


@app.route("/pictures/<filename>")
def pictures(filename):
    return send_from_directory(SAVE_DIR, filename)


@app.route("/delete/<filename>", methods=["POST"])
def delete_image(filename):
    # предпазване от ../ и други глупости
    safe_name = os.path.basename(filename)
    path = os.path.join(SAVE_DIR, safe_name)

    if os.path.exists(path):
        os.remove(path)
        print("Изтрита снимка:", path)
    else:
        print("Опит за триене на несъществуващ файл:", path)

    # връщаме потребителя там, откъдето е дошъл (index или gallery)
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

    # използваме същата preview страница
    return redirect(url_for("preview", filename=filename))


if __name__ == "__main__": app.run(debug=True)
