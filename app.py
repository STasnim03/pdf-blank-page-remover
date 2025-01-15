import os
from flask import Flask, request, redirect, url_for, send_file, jsonify
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract
from PyPDF2 import PdfReader, PdfWriter

# Path to the Tesseract executable
pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

app = Flask(__name__)

# Set the upload folder and allowed file types
UPLOAD_FOLDER = 'uploads/'
PROCESSED_FOLDER = 'processed/'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# Ensure upload and processed folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image):
    """
    Preprocesses an image for better OCR accuracy:
    - Converts to grayscale
    - Enhances contrast using adaptive contrast adjustment
    - Applies thresholding and noise filtering
    """
    gray_image = image.convert('L')
    enhanced_image = ImageOps.autocontrast(gray_image)
    threshold_image = enhanced_image.point(lambda p: 255 if p > 150 else 0)
    filtered_image = threshold_image.filter(ImageFilter.MedianFilter(3))
    return filtered_image

def is_blank_page(image):
    """
    Determines if a page is blank by using OCR to extract text.
    Returns True if no meaningful text is detected.
    """
    preprocessed_image = preprocess_image(image)
    text = pytesseract.image_to_string(preprocessed_image)
    return len(text.strip()) == 0

def remove_blank_pages(input_pdf_path, output_pdf_path, batch_size=5):
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()
    total_pages = len(reader.pages)

    for batch_start in range(0, total_pages, batch_size):
        batch_end = min(batch_start + batch_size, total_pages)
        images = convert_from_path(input_pdf_path, dpi=300, first_page=batch_start + 1, last_page=batch_end)

        for i, image in enumerate(images):
            page_number = batch_start + i
            if not is_blank_page(image):
                writer.add_page(reader.pages[page_number])

        print(f"Processed pages {batch_start + 1} to {batch_end}...")

    with open(output_pdf_path, "wb") as output_pdf:
        writer.write(output_pdf)

    print(f"Cleaned PDF saved to {output_pdf_path}")

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PDF Blank Page Remover</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
            }
            header {
                background-color: #333;
                color: white;
                padding: 10px;
                text-align: center;
            }
            form {
                margin: 20px auto;
                padding: 20px;
                max-width: 500px;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            }
            input[type="file"] {
                margin: 10px 0;
            }
            button {
                background-color: #333;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            button:hover {
                background-color: #555;
            }
            footer {
                background-color: #333;
                color: white;
                text-align: center;
                padding: 10px 0;
                position: fixed;
                width: 100%;
                bottom: 0;
            }
        </style>
    </head>
    <body>
        <header>
            <h1>PDF Blank Page Remover</h1>
        </header>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <p>Upload a PDF file to remove blank pages</p>
            <input type="file" name="file" accept="application/pdf" required>
            <button type="submit">Upload and Process</button>
        </form>
        <footer>
            <p>&copy; MIRPUR IT</p>
        </footer>
    </body>
    </html>
    """

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        input_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_pdf_path)

        # Define the output file path
        output_pdf_path = os.path.join(app.config['PROCESSED_FOLDER'], f"cleaned_{filename}")
        
        try:
            # Remove blank pages
            remove_blank_pages(input_pdf_path, output_pdf_path)
            return send_file(output_pdf_path, as_attachment=True)
        except Exception as e:
            return f"Error processing the file: {str(e)}"

    return redirect(request.url)

if __name__ == '__main__':
    app.run(debug=True)

