#!/usr/bin/env python3
"""
Script to remove white background from gangster sprite and save as PNG with transparency
"""
import requests
from PIL import Image
from io import BytesIO
import os

# Source image URL
SOURCE_URL = "https://customer-assets-wrfwihn1.emergentagent.net/wingman/2ee6fe9a-5f4c-4c9c-953d-61a038744d9e/attachments/b41101c4d68b4e3c88bec1eb1999f5c9_1788011836917.jpg"

# Output path
OUTPUT_PATH = "/app/backend/static/gangster_sprite.png"

def remove_white_background(image_url, output_path, tolerance=30):
    """
    Download image and remove white/near-white background, save as transparent PNG
    """
    # Download the image
    print(f"Downloading image from {image_url}...")
    response = requests.get(image_url)
    response.raise_for_status()
    
    # Open image
    img = Image.open(BytesIO(response.content))
    print(f"Image size: {img.size}, mode: {img.mode}")
    
    # Convert to RGBA if not already
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Get pixel data
    data = img.getdata()
    
    # Create new pixel data with transparent background
    new_data = []
    for item in data:
        # Check if pixel is white or near-white (within tolerance)
        r, g, b, a = item
        if r > 255 - tolerance and g > 255 - tolerance and b > 255 - tolerance:
            # Make transparent
            new_data.append((255, 255, 255, 0))
        else:
            # Keep original
            new_data.append(item)
    
    # Apply new pixel data
    img.putdata(new_data)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save as PNG with transparency
    img.save(output_path, 'PNG')
    print(f"Saved transparent sprite to {output_path}")
    
    return output_path

if __name__ == "__main__":
    remove_white_background(SOURCE_URL, OUTPUT_PATH)
    print("Done!")
