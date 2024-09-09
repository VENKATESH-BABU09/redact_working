from flask import Flask, render_template, request, redirect, url_for, send_file
from PIL import Image, ImageDraw
import pytesseract
import pdf2image
import re
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

# Define regex patterns for sensitive information
PII_PATTERNS = {
    'NAME': r'\b[A-Z][a-z]+\s[A-Z][a-z]+\b',  # Adjust as needed for name patterns
    'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b',
    'PHONE': r'\b\d{10}\b',  # Assuming 10 digit phone number
    'ACCOUNT': r'\b\d{9,18}\b',  # Generic account number pattern
    'AADHAAR': "^[2-9]{1}[0-9]{3}\\s[0-9]{4}\\s[0-9]{4}$",  # Aadhaar number pattern
    'DOB': r'\b\d{2}/\d{2}/\d{4}\b',  # Assuming date of birth in dd/mm/yyyy format
    # Add other patterns as needed
}

# Supported languages (English, Tamil, Hindi)
LANGUAGES = 'eng+tam+hin'

def detect_pii_and_mask(image_path):
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    
    # Use pytesseract to perform OCR on the image
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, lang=LANGUAGES)
    
    # Iterate over the detected text
    for i, word in enumerate(data['text']):
        if word.strip():  # Ensure the word is not empty
            # Check against PII patterns
            if any(re.match(pattern, word) for pattern in PII_PATTERNS.values()) and int(data['conf'][i]) > 60:
                (x, y, w, h) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                draw.rectangle([x, y, x + w, y + h], fill="black")

    masked_image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'masked_' + os.path.basename(image_path))
    image.save(masked_image_path)
    
    return masked_image_path

def process_pdf_and_redact(pdf_path):
    # Convert PDF to images
    images = pdf2image.convert_from_path(pdf_path)
    redacted_images = []

    for i, image in enumerate(images):
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], f'page_{i+1}.png')
        image.save(image_path)
        
        # Redact sensitive information in the image
        masked_image_path = detect_pii_and_mask(image_path)
        redacted_images.append(masked_image_path)
    
    # Save the redacted images back to a single PDF
    pdf_output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'redacted_output.pdf')
    images = [Image.open(img_path).convert('RGB') for img_path in redacted_images]
    images[0].save(pdf_output_path, save_all=True, append_images=images[1:])
    
    return pdf_output_path

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'image' not in request.files:
            return 'No file part'
        
        file = request.files['image']
        if file.filename == '':
            return 'No selected file'
        
        if file:
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            if filename.lower().endswith('.pdf'):
                masked_pdf_path = process_pdf_and_redact(filepath)
                return send_file(masked_pdf_path, as_attachment=True)
            elif filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                masked_image_path = detect_pii_and_mask(filepath)
                return redirect(url_for('uploaded_file', filename=os.path.basename(masked_image_path)))
            else:
                return 'Unsupported file type'
    
    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return render_template('uploaded.html', filename=filename)

if __name__ == '__main__':
    app.run(debug=True)
