import os
import zipfile
import io
from flask import Flask, request, render_template, send_file, send_from_directory
from Automation import take_screenshot
from generate_reports import generate_report, generates_report
from Gen_Ai_Comparision import compare_screenshots

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

# Use absolute paths for consistency
BASE_DIR = os.getcwd()
SCREENSHOTS_FOLDER = os.path.join(BASE_DIR, "backend", "screenshots")

# Ensure required folders exist
os.makedirs(SCREENSHOTS_FOLDER, exist_ok=True)

# Function to delete files after use
def delete_files_after_use(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

# Route to serve screenshots (if needed)
@app.route('/screenshots/<filename>')
def serve_screenshot(filename):
    return send_from_directory(SCREENSHOTS_FOLDER, filename)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    urls = request.form.getlist('url')
    references = request.files.getlist('reference')
    images1 = request.files.getlist('image1')
    images2 = request.files.getlist('image2')
    url1 = request.form.get('url1')  # First URL for comparison
    url2 = request.form.get('url2')  # Second URL for comparison

    comparison_results = []

    # Process URL and reference image comparison
    if urls and references and len(urls) == len(references):
        for url, reference in zip(urls, references):
            # Capture screenshot for the provided URL
            screenshot_path = take_screenshot(url)

            # Save the uploaded reference image into the screenshots folder
            ref_path = os.path.join(SCREENSHOTS_FOLDER, reference.filename)
            reference.save(ref_path)

            # Compare the screenshots and create the merged image
            comparison_result, merged_image_path = compare_screenshots(screenshot_path, ref_path)
            if not merged_image_path:
                print(f"Error: Failed to merge images for URL: {url}")
                continue

            # Generate an HTML report
            report_content = generate_report(comparison_result, screenshot_path, ref_path, merged_image_path, url)
            comparison_results.append(report_content)

    # Process uploaded image pairs comparison
    if images1 and images2 and len(images1) == len(images2):
        for image1, image2 in zip(images1, images2):
            # Save the uploaded images into the screenshots folder
            screenshot_path = os.path.join(SCREENSHOTS_FOLDER, image1.filename)
            ref_path = os.path.join(SCREENSHOTS_FOLDER, image2.filename)
            image1.save(screenshot_path)
            image2.save(ref_path)

            # Compare the uploaded images and create the merged image
            comparison_result, merged_image_path = compare_screenshots(screenshot_path, ref_path)
            if not merged_image_path:
                print(f"Error: Failed to merge uploaded images: {image1.filename} and {image2.filename}")
                continue

            # Generate an HTML report
            report_content = generates_report(comparison_result, screenshot_path, ref_path, merged_image_path)
            comparison_results.append(report_content)

    # Process two URLs comparison
    if url1 and url2:
        # Capture screenshots for both URLs
        screenshot1_path = take_screenshot(url1)
        screenshot2_path = take_screenshot(url2)

        # Compare the screenshots and create the merged image
        comparison_result, merged_image_path = compare_screenshots(screenshot1_path, screenshot2_path)
        if not merged_image_path:
            print(f"Error: Failed to merge screenshots for URLs: {url1} and {url2}")
        else:
            # Generate an HTML report
            report_content = generate_report(comparison_result, screenshot1_path, screenshot2_path, merged_image_path, f"{url1} vs {url2}")
            comparison_results.append(report_content)

    if not comparison_results:
        return "Error: No valid comparisons could be performed.", 500

    # Build a ZIP file containing all generated HTML reports
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        for i, report_content in enumerate(comparison_results):
            zipf.writestr(f"Visual_Test_Report_{i+1}.html", report_content)

    zip_buffer.seek(0)

    # Optionally, clean up the screenshots folder after processing
    delete_files_after_use(SCREENSHOTS_FOLDER)

    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='Visual_Test_Reports.zip'
    )

if __name__ == '__main__':
    app.run(debug=True)