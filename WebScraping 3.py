from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv 

def extract_popup_info(driver):
    popup_info = {}
    try:
        # Wait for the popup to appear
        print("Waiting for popup to be present...")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'Popup')))
        print("Popup is present.")

        # Find the popup element
        popup = driver.find_element(By.CLASS_NAME, 'Popup')

        def safe_get_text(by, value):
            # Retrieve text from an element, return 'N/A' if not found
            elements = popup.find_elements(by, value)
            return elements[0].text if elements else 'N/A'
        
        def safe_get_attribute(by, value, attribute):
            # Retrieve an attribute value from an element, return 'N/A' if not found
            elements = popup.find_elements(by, value)
            return elements[0].get_attribute(attribute) if elements else 'N/A'

        def find_phone_number(popup):
            # Look for phone number patterns within the popup
            potential_phone_numbers = popup.find_elements(By.XPATH, "//span[h3[text()='Contact']]/span/p")
            for element in potential_phone_numbers:
                text = element.text
                if text and text.startswith('0') and any(char.isdigit() for char in text):
                    return text
            return 'N/A'

        def find_website(popup):
             # Search for a website URL within the popupc
            potential_websites = popup.find_elements(By.XPATH, "//span[h3[text()='Contact']]/span/a")
            for element in potential_websites:
                href = element.get_attribute('href')
                if href and href.startswith('http'):
                    return href
            return 'N/A'

        def split_address_and_postcode(address):
            # Split address into address and postcode
            parts = [part.strip() for part in address.split(',')]
            if len(parts) > 1:
                postcode_part = parts[-1]
                address_part = ', '.join(parts[:-1])
                return address_part, postcode_part
            return address, 'N/A'

        # Extract popup data
        print("Extracting popup data...")
        h2 = safe_get_text(By.TAG_NAME, 'h2')
        h4 = safe_get_text(By.TAG_NAME, 'h4')
        description = safe_get_text(By.XPATH, "//span[h3[text()='Description']]/p")
        areas_of_work = safe_get_text(By.XPATH, "//span[h3[text()='Areas of Work']]/p")
        website = find_website(popup)
        contact_phone = find_phone_number(popup)
        full_address = safe_get_text(By.XPATH, "//span[h3[text()='Address']]/p")
        address, postcode = split_address_and_postcode(full_address)

        # Store extracted data in dictionary
        popup_info = {
            'Name': h2,
            'Type': h4,
            'Description': description,
            'Areas of Work': areas_of_work,
            'Website': website,
            'Contact Phone': contact_phone,
            'Address': address,
            'Postcode': postcode
        }

        print("Popup data extracted successfully.")

    # Handle exceptions during data extraction
    except Exception as e:
        print(f"Error extracting popup info: {e}")

    return popup_info

def close_popup(driver):
    try:
        # Wait for the close button to be clickable
        print("Attempting to find close button...")
        close_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//input[@value='close']")))
        print("Close button found, clicking...")
        close_button.click()
        # Wait until the close button is no longer present
        WebDriverWait(driver, 5).until(EC.staleness_of(close_button))
        print("Popup closed successfully.")
    # Handle exceptions during popup closing
    except Exception as e:
        print(f"Could not close popup: {e}")

try:
    # Set up the WebDriver
    print("Setting up the WebDriver...")
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    print("WebDriver setup complete.")

    # Navigate to the target webpage
    print("Navigating to the main webpage...")
    driver.get('https://integratecic.my.salesforce-sites.com/directory/')
    print("Navigated to main page.")

    all_ids = set() # Track processed IDs
    collected_data = set() # Store unique popup data

    while True:
        # Wait for all anchor tags to be present
        print("Waiting for anchor tags to load...")
        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'resultsBlock')))
        print("Anchor tags loaded.")

        # Fetch anchor tags
        anchor_tags = driver.find_elements(By.CLASS_NAME, 'resultsBlock')
        print(f"Found {len(anchor_tags)} anchor tags on the current page.")

        if not anchor_tags:
            print("No anchor tags found on the current page.")
            break

        # Click on each anchor tag with a specific ID ending
        for tag in anchor_tags:
            tag_id = tag.get_attribute('id')
            all_ids = set() # Clear the set of IDs after each page 
            if tag_id and tag_id.endswith(':j_id39'):
                if tag_id not in all_ids:
                    all_ids.add(tag_id)
                    print(f"Clicking on link with id: {tag_id}")
                    
                    try:
                        # Ensure the element is clickable
                        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(tag))
                        tag.click()
                        print("Link clicked, waiting for popup...")

                        # Wait for the popup to appear and extract information
                        popup_info = extract_popup_info(driver)
                        if popup_info:
                            print("Popup info collected:")
                            print(popup_info)
                            # Convert to a tuple to store in the set (for uniqueness)
                            collected_data.add(tuple(popup_info.items()))
                    except Exception as e:
                        print(f"Error while interacting with tag {tag_id}: {e}")

                    # Close the popup
                    close_popup(driver)
                    time.sleep(1)  # Sleep to ensure popup closes properly

        # Try to find the 'Next Page' button by text
        try:
            print("Waiting for 'Next Page' button...")
            next_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, 'Next Page >')))
            print("Found 'Next Page' button, clicking...")
            next_button.click()
            print("Clicked 'Next Page' button, waiting for page to load...")
            WebDriverWait(driver, 20).until(EC.staleness_of(next_button))  # Wait until the next button is no longer stale
            print("Navigated to the next page.")
        except Exception as e:
            print(f"Could not find or click 'Next Page' button: {e}")
            # If the next button is not found or clickable, break the loop
            break

    print(f"Total number of unique popups collected: {len(collected_data)}")

    # Write collected data to CSV file
    with open('popup_data.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Name', 'Type', 'Description', 'Areas of Work', 'Website', 'Contact Phone', 'Address', 'Postcode']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for data in collected_data:
            writer.writerow(dict(data))  # Convert tuple back to dictionary

    print("Data written to popup_data.csv successfully.")

except Exception as e:
    print("An error occurred:", e)

finally:
    # Close the WebDriver
    if 'driver' in locals():
        print("Closing the WebDriver...")
        driver.quit()
        print("WebDriver closed.")
