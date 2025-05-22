import os
import logging
from pdf2image import convert_from_path
from config.settings import POPPLER_PATH, TEMP_DIR, ATTACHMENT_IMAGES_DIR

# Configure logging
logger = logging.getLogger(__name__)

def convert_pdf_to_images(pdf_path, message_id):
    """
    Convert a PDF file to images.
    
    Args:
        pdf_path: Path to the PDF file
        message_id: ID of the email message (used for naming)
    
    Returns:
        list: List of paths to the generated images
    """
    try:
        # Create output directory
        output_dir = os.path.join(ATTACHMENT_IMAGES_DIR, message_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Convert PDF to images
        images = convert_from_path(
            pdf_path,
            500,  # DPI
            poppler_path=POPPLER_PATH,
            output_folder=output_dir,
            fmt='png'
        )
        
        logger.info(f"Converted PDF to {len(images)} images")
        
        # Return the paths to the images
        image_paths = [os.path.join(output_dir, f"page_{i+1}.png") for i in range(len(images))]
        return image_paths
    
    except Exception as e:
        logger.error(f"Error converting PDF to images: {e}")
        return []

def clean_temp_files(message_id=None):
    """
    Clean temporary files.
    
    Args:
        message_id: Optional ID of the email message to clean files for.
                   If None, all temporary files will be cleaned.
    """
    try:
        if message_id:
            # Clean files for a specific message
            temp_file_pattern = f"{message_id}_*"
            for file in os.listdir(TEMP_DIR):
                if file.startswith(message_id):
                    os.remove(os.path.join(TEMP_DIR, file))
            
            # Clean image directory for the message
            image_dir = os.path.join(ATTACHMENT_IMAGES_DIR, message_id)
            if os.path.exists(image_dir):
                for file in os.listdir(image_dir):
                    os.remove(os.path.join(image_dir, file))
                os.rmdir(image_dir)
            
            logger.info(f"Cleaned temporary files for message {message_id}")
        else:
            # Clean all temporary files
            for file in os.listdir(TEMP_DIR):
                os.remove(os.path.join(TEMP_DIR, file))
            
            logger.info("Cleaned all temporary files")
    
    except Exception as e:
        logger.error(f"Error cleaning temporary files: {e}")