import os
import json
from functools import wraps
import webview

from flask import Flask, render_template, request, send_from_directory
from werkzeug.wrappers import BaseResponse as Response

from contextlib import redirect_stdout
from io import StringIO


template_dir = os.path.join(os.path.dirname(__file__), 'static')
static_dir = os.path.join(os.path.dirname(__file__), 'static')

webview.gui = 'gtk'

app = Flask(__name__,
            static_url_path='',
            template_folder=template_dir)

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1  # disable caching


@app.route('/js/<path:path>')
def send_js(path):
    js_dir = os.path.join(static_dir, 'js')
    return send_from_directory(js_dir, path)


@app.route('/css/<path:path>')
def send_css(path):
    css_dir = os.path.join(static_dir, 'css')
    return send_from_directory(css_dir, path)


@app.route('/fonts/<path:path>')
def send_fonts(path):
    font_dir = os.path.join(static_dir, 'fonts')
    return send_from_directory(font_dir, path)


@app.route('/[img|images]/<path:path>')
def send_images(path):
    font_dir = os.path.join(static_dir, 'images')
    return send_from_directory(font_dir, path)


def verify_token(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        data = json.loads(request.data)
        token = data.get('token')
        if token == webview.token:
            return function(*args, **kwargs)
        else:
            raise Exception('Authentication error')

    return wrapper


@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.route('/')
def root():
    """
    Render index.html. Initialization is performed asynchronously in initialize() function
    """
    return render_template('index.html', token=webview.token)


@app.route('/init', methods=['POST'])
@verify_token
def initialize():
    '''
    Perform heavy-lifting initialization asynchronously.
    :return:
    '''
    can_start = webapi.initialize()

    if can_start:
        return Response('ok', status=200)
    else:
        return Response('error', status=500)


def main():
    stream = StringIO()
    try:
        with redirect_stdout(stream):
            window = webview.create_window('TERMINAL',
                                           app,
                                           fullscreen=True)
            webview.start(debug=True)
    except Exception:
        raise


if __name__ == "__main__":
    main()
