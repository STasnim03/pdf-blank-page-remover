import os
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_path

app = Flask(__name__)

# Configure the upload and processed folders
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# Allowed extensions for file upload
ALLOWED_EXTENSIONS = {'pdf'}

# Make sure the folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to check if a page is blank
def is_blank_page(image):
    return image.getbbox() is None

# Function to remove blank pages from PDF
def remove_blank_pages(input_pdf_path, output_pdf_path, batch_size=5):
    try:
        with open(input_pdf_path, "rb") as input_file:
            reader = PdfReader(input_file)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        raise Exception("Error reading the PDF file.")

    writer = PdfWriter()
    total_pages = len(reader.pages)

    # Process the pages in batches
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

# Route to upload and process PDF
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        input_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_pdf_path)

        # Log the file path for debugging
        print(f"File saved at: {input_pdf_path}")

        # Validate the PDF file
        if not os.path.isfile(input_pdf_path):
            return jsonify({"error": "Invalid PDF file. Please upload a valid PDF."}), 400

        # Output file path
        output_pdf_filename = f"cleaned_{filename}"
        output_pdf_path = os.path.join(app.config['PROCESSED_FOLDER'], output_pdf_filename)

        # Process the PDF
        try:
            remove_blank_pages(input_pdf_path, output_pdf_path)
        except Exception as e:
            return jsonify({"error": f"Error processing the file: {str(e)}"}), 500

        return send_file(output_pdf_path, as_attachment=True)

    return jsonify({"error": "Invalid file format. Please upload a valid PDF."}), 400

# Route for the index page
@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PDF Blank Page Remover</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }
            header { background-color: #333; color: white; padding: 10px; text-align: center; }
            form { margin: 20px auto; padding: 20px; max-width: 500px; background-color: white; border-radius: 8px; box-shadow: 0 0 10px rgba(0, 0, 0, 0.1); }
            input[type="file"] { margin: 10px 0; }
            button { background-color: #333; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background-color: #555; }
            footer { background-color: #333; color: white; text-align: center; padding: 10px 0; position: fixed; width: 100%; bottom: 0; }
        </style>
    </head>
    <body>
        <header>
            <h1>PDF Blank Page Remover</h1>
        </header>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <p>Upload a PDF file to remove blank pages.</p>
            <input type="file" name="file" accept="application/pdf" required>
            <button type="submit">Upload and Process</button>
        </form>
        <footer>
            <p>&copy; 2025 Mirpur IT</p>
        </footer>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(debug=True)
