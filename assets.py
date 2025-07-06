import os

# Define the path to the images directory
image_folder = "assets"

# List all image files
image_files = [f for f in os.listdir(image_folder) if os.path.isfile(os.path.join(image_folder, f))]

# Print image file names
print("Image files found:")
for image in image_files:
    print(image)
