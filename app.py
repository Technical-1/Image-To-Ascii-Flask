#!/usr/bin/env python3
"""
Flask web application for converting images to ASCII art.
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, make_response
import os
from io import BytesIO
from generate_ascii import image_to_ascii

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg'}

# Conversion defaults / bounds
DEFAULT_CHARS = '@%#*+=-:. '
MIN_DIMENSION = 1
MAX_DIMENSION = 300  # caps the LANCZOS resize so a request can't exhaust memory

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def parse_dimension(raw, default):
    """Parse a width/height form value, clamped to [MIN_DIMENSION, MAX_DIMENSION].

    Returns the default for missing/empty values, and None for a value that is
    present but not a valid integer (so the caller can return a 400).
    """
    if raw is None or raw == '':
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return max(MIN_DIMENSION, min(MAX_DIMENSION, value))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.png')
def favicon_png():
    response = make_response(send_from_directory(app.static_folder, 'favicon.png', mimetype='image/png'))
    response.headers['Cache-Control'] = 'public, max-age=31536000'
    return response

@app.route('/favicon.ico')
def favicon_ico():
    response = make_response(send_from_directory(app.static_folder, 'favicon.png', mimetype='image/png'))
    response.headers['Cache-Control'] = 'public, max-age=31536000'
    return response

@app.route('/logo.png')
def logo():
    return send_from_directory(app.static_folder, 'logo.png', mimetype='image/png')

@app.route('/convert', methods=['POST'])
def convert():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    # Validate parameters (return 400s, not 500s, for bad client input)
    width = parse_dimension(request.form.get('width'), 50)
    height = parse_dimension(request.form.get('height'), 30)
    if width is None or height is None:
        return jsonify({'error': 'Width and height must be integers'}), 400

    # An empty chars field falls back to the default set (avoids a crash downstream)
    chars = request.form.get('chars') or DEFAULT_CHARS

    ext = file.filename.rsplit('.', 1)[1].lower()
    try:
        if ext == 'svg':
            # Pillow can't decode SVG; rasterize to PNG first.
            import cairosvg
            png_bytes = cairosvg.svg2png(bytestring=file.read())
            image_source = BytesIO(png_bytes)
        else:
            image_source = file

        ascii_lines = image_to_ascii(image_source, width, height, chars)
    except Exception:
        # Log the real error server-side; don't leak internals to the client.
        app.logger.exception('Failed to convert image')
        return jsonify({'error': 'Could not process the image. Please try a different file.'}), 500

    return jsonify({
        'success': True,
        'ascii': '\n'.join(ascii_lines),
        'lines': ascii_lines
    })

if __name__ == '__main__':
    import sys
    # Use port from environment variable (for Render) or default to 5001
    port = int(os.environ.get('PORT', 5001))
    # Use port from command line if provided (for local development)
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    # Disable debug mode in production
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)
