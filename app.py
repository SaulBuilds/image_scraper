from flask import Flask, request, render_template
import os
import time
import requests
from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions as selexcept

# Initialize Flask app
app = Flask(__name__)

# ChromeDriver setup
chrome_service = Service('/usr/local/bin/chromedriver')  # Replace with your ChromeDriver path
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Headless mode for background operation
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(service=chrome_service, options=options)

# Image storage folder
IMAGES_DIR = "static/images"
os.makedirs(IMAGES_DIR, exist_ok=True)

# Main route to display the search form and results
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        query = request.form.get('query')
        num_images = int(request.form.get('num_images', 200))
        
        if query:
            search_images(query, IMAGES_DIR, num_images)
            images = os.listdir(IMAGES_DIR)
            return render_template("index.html", query=query, images=images)
    
    return render_template("index.html", query=None, images=[])

# Function to search images on Google and download them
def search_images(query, download_folder, num_images=200):
    # Clear the download folder before saving new images
    for filename in os.listdir(download_folder):
        os.remove(os.path.join(download_folder, filename))

    # Navigate to Google Images and perform the search
    driver.get("https://images.google.com")
    try:
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        search_box.send_keys(query + Keys.RETURN)
    except selexcept.TimeoutException:
        print("Timeout: Google Images search box did not load.")
        return

    # Collect image URLs
    image_urls = set()
    while len(image_urls) < num_images:
        thumbnails = driver.find_elements(By.CSS_SELECTOR, "img.Q4LuWd")
        
        # Loop through thumbnails to get full-size images
        for img in thumbnails[len(image_urls):num_images]:
            try:
                img.click()  # Click to view full-size image
                time.sleep(1)
                
                # Get full-size image URL
                large_image = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "img.n3VNCb"))
                )
                url = large_image.get_attribute("src")
                
                # Add URL if valid
                if url and url.startswith("http"):
                    image_urls.add(url)
                    print(f"Collected {len(image_urls)} image URLs.")
                if len(image_urls) >= num_images:
                    break
            except (selexcept.StaleElementReferenceException, selexcept.TimeoutException):
                print("Error: Retrying thumbnail click or URL fetch.")
        
        # Scroll down to load more images
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Pause to allow more images to load

    # Download images to specified folder
    for idx, url in enumerate(image_urls):
        try:
            response = requests.get(url, timeout=5)
            img = Image.open(BytesIO(response.content))
            img.save(f"{download_folder}/{query}_{idx+1}.jpg", "JPEG")
            print(f"Downloaded image {idx+1}")
        except Exception as e:
            print(f"Error downloading image {idx+1}: {e}")

# Shutdown route to close the Selenium driver safely
@app.route('/shutdown', methods=['POST'])
def shutdown():
    driver.quit()
    return "Browser closed", 200

# Run Flask app
if __name__ == '__main__':
    app.run(debug=True)
