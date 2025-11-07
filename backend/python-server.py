from dotenv import load_dotenv
load_dotenv()

import os
import io
import uuid
from datetime import datetime
import json
import re
import subprocess
import sys
from flask import Flask, request, jsonify, send_from_directory, send_file


import gspread
from google.oauth2.service_account import Credentials

def connect_to_sheet():
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("UserCredentials").worksheet("Data")
        print("✅ Connected to Google Sheet: UserCredentials → Data")
        return sheet
    except Exception as e:
        print(f"❌ Error connecting to Google Sheets: {e}")
        return None  # Return None instead of raising


import uuid
import smtplib
from email.mime.text import MIMEText
from threading import Thread
import time
import requests

def send_reset_email(email, token):
    """
    Sends reset email using Google Apps Script Web App.
    """
    try:
        apps_script_url = "https://script.google.com/macros/s/AKfycbwILFRXaL-mo7Gr7IH5HujSkN3vxYytYr_4097xh26C4EsoK-nYHFThaHKx3T5oZmjk/exec"
        payload = {"email": email, "token": token}

        response = requests.post(apps_script_url, json=payload)
        response.raise_for_status()

        result = response.json()
        if result.get("success"):
            print(f"✅ Reset email sent successfully to {email}")
        else:
            print(f"⚠️ Apps Script responded with error: {result.get('error')}")
    except Exception as e:
        print(f"❌ Error sending reset email via Apps Script: {e}")


from flask_cors import CORS
from PIL import Image
import google.generativeai as genai
from google.cloud import storage
from google.generativeai import types
from google.cloud.exceptions import Forbidden


app = Flask(__name__)

# ✅ Enable CORS properly for your frontend
CORS(app, resources={r"/*": {
    "origins": [
        "http://localhost:5173",
        "https://listro-frontend-648176215467.asia-south1.run.app"
    ]
}})

# --- CONFIGURATION ---


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
   raise ValueError("Gemini API Key (GOOGLE_API_KEY) missing in .env file")


genai.configure(api_key=GOOGLE_API_KEY)


# Separate models for text and image generation
TEXT_MODEL_ID = "gemini-2.5-flash"
IMAGE_MODEL_ID = "gemini-2.5-flash-image-preview"


try:
   # Text model for text generation
   text_model = genai.GenerativeModel(TEXT_MODEL_ID)
   print(f"âœ“ Gemini Text model initialized: {TEXT_MODEL_ID}")
except Exception as e:
   print(f"âœ— Text model initialization error: {e}")
   raise


try:
   # Image model for image generation
   image_model = genai.GenerativeModel(IMAGE_MODEL_ID)
   print(f"âœ“ Gemini Image model initialized: {IMAGE_MODEL_ID}")
except Exception as e:
   print(f"âœ— Image model initialization error: {e}")
   raise


OUTPUT_DIR = "generated_images"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# --- GOOGLE CLOUD STORAGE CONFIG ---


GCS_BUCKET_NAME = "amz-image-stores"


try:
   storage_client = storage.Client()
   print("âœ“ Google Cloud Storage client initialized.")
except Exception as e:
   print(f"âœ— GCS client initialization error: {e}")
   storage_client = None  # Fail gracefully


def upload_to_gcs(local_file_path, destination_blob_name):
   """
   Uploads a file to GCS, makes it public, and returns the public URL.
   """
   if not storage_client:
       raise Exception("GCS client not available")


   bucket = storage_client.bucket(GCS_BUCKET_NAME)
   blob = bucket.blob(destination_blob_name)
   try:
       print(f"DEBUG: Uploading {local_file_path} to gs://{GCS_BUCKET_NAME}/{destination_blob_name}")
       blob.upload_from_filename(local_file_path)
       gcs_public_url = blob.public_url
       print(f"âœ“ Uploaded to GCS. Public URL: {gcs_public_url}")
       return gcs_public_url
   except Forbidden:
       error_message = f"GCS Permission Denied (403): Ensure ADC user has 'Storage Admin' role for bucket '{GCS_BUCKET_NAME}'."
       print(f"âœ— GCS upload failed: {error_message}")
       raise Exception(error_message)
   except Exception as e:
       error_message = f"GCS Upload Failed: {type(e).__name__} - {str(e)}"
       print(f"âœ— GCS upload failed: {error_message}")
       raise Exception(error_message)


# --- PROMPT FUNCTIONS for IMAGE GENERATION ---


def get_prompt_amazon_main_image():
   return (
       "High-quality professional fashion product photo for an Amazon listing main image. "
       "The entire product must be shown, without being cropped, with a pure white background (RGB 255,255,255, hex #FFFFFF), "
       "and the model standing upright. "
       "Strict note: Keep the uploaded dress exactly as it is. Do not change the color, pattern, or design under any circumstances. "
       "The product must fill at least 85% but not touch the image borders. "
       "No props, no accessories, no packaging, no text, badges, graphics, or watermarks. "
       "No mannequin, From head to toe, only a human model. Sharp focus, true-to-color, professional lighting. "
       "Image must be at least 1600x1600 pixels. "
       "Category: [Category], Gender: [Gender], Age Group: [AgeGroup], Style: [Style], Subcategory: [SubCategory]"
   )


def get_prompt_amazon_product_only_image():
   return (
       "Amazon fashion category compliant product image. Present the single product, fully visible, with a pure white background (RGB 255,255,255, hex #FFFFFF). "
       "Product must fill 85%-90% of the frame but should not touch the edge. "
       "Strict note: Keep the uploaded dress exactly as it is. Do not change the color, pattern, or design under any circumstances. "
       "Do not include human body, model, props, accessories, packaging, text, logos, watermarks, badges, or additional graphics. "
       "The image must be sharp, clear, and reflect true product color and details. "
       "At least 1600x1600px resolution. "
       "Category: [Category], Gender: [Gender], Age Group: [AgeGroup], Style: [Style], Subcategory: [SubCategory]"
   )


def get_prompt_amazon_lifestyle_image():
   return (
       "Lifestyle/gallery image for Amazon fashion. Show the model wearing the product in a real-world, vibrant event or indoor setting "
       "(such as a boutique, studio, wedding, or party scene). "
       "Strict note: Keep the uploaded dress exactly as it is. Do not change the color, pattern, or design under any circumstances. "
       "The product must remain the focus, fully visible, without text, watermarks, or unrelated props. "
       "Professional, realistic lighting only. Pure white background NOT required for this type. "
       "Category: [Category], Gender: [Gender], Age Group: [AgeGroup], Style: [Style], Subcategory: [SubCategory]"
   )


def get_prompt_amazon_angle_image():
   return (
       "Amazon-compliant model image, showing a left, right, or back view. "
       "Model must be standing from head to toe, product fully in frame, at least 85% of the image, not cut off. "
       "Strict note: Keep the uploaded dress exactly as it is. Do not change the color, pattern, or design under any circumstances. "
       "No text, graphics, badges, watermarks, packaging, or unrelated props. "
       "Clean, subtle festive or indoor background permitted, but product remains clearly visible. "
       "Category: [Category], Gender: [Gender], Age Group: [AgeGroup], Style: [Style], Subcategory: [SubCategory]"
   )


def get_prompt_amazon_infographic():
   return (
       "Infographic gallery image for Amazon fashion product, showing the traditional suit centered on soft pastel (not pure white) background. "
       "Include minimalist icons and a clean Product Details sectionâ€”use minimal, readable text, clear separation, NO overlaying text on product and NO spelling errors. "
       "The product must remain the focus and fully visible. At least 1600x1600px resolution. "
       "Strict note: Keep the uploaded dress exactly as it is. Do not change the color, pattern, or design under any circumstances. "
       "No cropping, all text complete and readable, professional high-end appearance. "
       "Category: [Category], Gender: [Gender], Age Group: [AgeGroup], Style: [Style], Subcategory: [SubCategory]"
   )


PROMPT_FUNCTIONS = [
   get_prompt_amazon_main_image,
   get_prompt_amazon_product_only_image,
   get_prompt_amazon_lifestyle_image,
   get_prompt_amazon_angle_image,
   get_prompt_amazon_infographic
]


def replace_placeholders(prompt: str, attributes: dict) -> str:
   pattern = r"\[(\w+)\]"
   def replacer(match):
       key = match.group(1)
       return attributes.get(key, f"[{key}]")
   return re.sub(pattern, replacer, prompt)





# Fallback user data when Google Sheets is not available
FALLBACK_USERS = {
    "admin@listro.com": {"password": "admin123", "first_time": False},
    "test@listro.com": {"password": "test@listro.com", "first_time": True},  # First time user
    "demo@listro.com": {"password": "demo123", "first_time": False}
}

# --- AUTHENTICATION ENDPOINTS ---

@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        if not email or not password:
            return jsonify({"success": False, "error": "Email and password are required"}), 400

        # Try to connect to Google Sheets first
        sheet = connect_to_sheet()
        
        if sheet is not None:
            # Google Sheets is available - use it
            try:
                records = sheet.get_all_records()
                print(f"🔍 Google Sheets records found: {len(records)}")
                print(f"🔍 Looking for email: {email}")
                
                # Debug: Print first few records (without passwords for security)
                for i, record in enumerate(records[:3]):
                    debug_record = {k: v if k != 'password' else '***' for k, v in record.items()}
                    print(f"🔍 Record {i}: {debug_record}")

                # Find user by email (handle both lowercase and capitalized column names)
                user_record = None
                for record in records:
                    # Try both 'email'/'Email' and handle different casing
                    record_email = record.get("email", record.get("Email", "")).strip().lower()
                    if record_email == email:
                        user_record = record
                        print(f"✅ Found user record for {email}")
                        break

                if not user_record:
                    print(f"❌ No user found for email: {email}")
                    return jsonify({"success": False, "error": "Invalid email or password"}), 401

                # Check if password matches (handle both lowercase and capitalized column names)
                stored_password = str(user_record.get("password", user_record.get("Password", ""))).strip()
                print(f"🔍 Stored password: {stored_password}, Input password: {password}")
                
                if password != stored_password:
                    return jsonify({"success": False, "error": "Invalid email or password"}), 401

                # Check if it's first time login - check FirstLogin column or if password equals email
                first_login_flag = user_record.get("FirstLogin", user_record.get("firstLogin", "")).strip().lower()
                first_time = first_login_flag == "yes" or stored_password == email

                return jsonify({
                    "success": True, 
                    "message": "Login successful",
                    "first_time": first_time,
                    "email": email
                })
            except Exception as sheets_error:
                print(f"❌ Google Sheets error, falling back to local auth: {sheets_error}")
                # Fall through to fallback authentication
        
        # Fallback authentication when Google Sheets is not available
        print("🔄 Using fallback authentication system")
        
        if email not in FALLBACK_USERS:
            return jsonify({"success": False, "error": "Invalid email or password"}), 401
        
        user_data = FALLBACK_USERS[email]
        if password != user_data["password"]:
            return jsonify({"success": False, "error": "Invalid email or password"}), 401
        
        return jsonify({
            "success": True, 
            "message": "Login successful (fallback mode)",
            "first_time": user_data["first_time"],
            "email": email
        })

    except Exception as e:
        print(f"❌ Login error: {e}")
        return jsonify({"success": False, "error": "Server error during login"}), 500


@app.route("/reset-password", methods=["POST"])
def reset_password():
    try:
        data = request.get_json()
        email = data.get("email", "").strip().lower()

        if not email:
            return jsonify({"success": False, "error": "Email is required"}), 400

        # Try to connect to Google Sheets first
        sheet = connect_to_sheet()
        
        if sheet is not None:
            # Google Sheets is available
            try:
                records = sheet.get_all_records()
                # Check both lowercase and capitalized column names
                user_exists = any(
                    record.get("email", record.get("Email", "")).strip().lower() == email 
                    for record in records
                )
                
                if not user_exists:
                    return jsonify({"success": False, "error": "Email not found"}), 404

                # Generate reset token and send email
                reset_token = str(uuid.uuid4())
                send_reset_email(email, reset_token)
                
                return jsonify({
                    "success": True, 
                    "message": "Reset link sent to your email",
                    "pending_approval": False
                })
            except Exception as sheets_error:
                print(f"❌ Google Sheets error, using fallback: {sheets_error}")
        
        # Fallback mode
        print("🔄 Using fallback password reset")
        
        if email not in FALLBACK_USERS:
            return jsonify({"success": False, "error": "Email not found"}), 404
        
        # In fallback mode, just return success without actually sending email
        return jsonify({
            "success": True, 
            "message": "Password reset simulated (fallback mode). Use demo credentials.",
            "pending_approval": False
        })

    except Exception as e:
        print(f"❌ Reset password error: {e}")
        return jsonify({"success": False, "error": "Server error during password reset"}), 500


@app.route("/update-password", methods=["POST"])
def update_password():
    try:
        data = request.get_json()
        email = data.get("email", "").strip().lower()
        new_password = data.get("password", "").strip()
        token = data.get("token", "")  # Reset token (not implemented in this basic version)

        if not email or not new_password:
            return jsonify({"success": False, "error": "Email and password are required"}), 400

        # Try to connect to Google Sheets first
        sheet = connect_to_sheet()
        
        if sheet is not None:
            # Google Sheets is available
            try:
                records = sheet.get_all_records()

                # Find user by email (handle both lowercase and capitalized column names)
                user_record = None
                row_index = None
                for i, record in enumerate(records):
                    record_email = record.get("email", record.get("Email", "")).strip().lower()
                    if record_email == email:
                        user_record = record
                        row_index = i + 2  # +2 because enumerate starts at 0 and sheet rows start at 1, plus header
                        break

                if not user_record:
                    return jsonify({"success": False, "error": "User not found"}), 404

                # Update password in Google Sheets - find the Password column
                # First, get the header row to find the correct column index
                header_row = sheet.row_values(1)
                password_col = None
                for col_idx, header in enumerate(header_row):
                    if header.lower() == 'password':
                        password_col = col_idx + 1  # gspread uses 1-based indexing
                        break
                
                if password_col:
                    sheet.update_cell(row_index, password_col, new_password)
                    # Also update FirstLogin to 'No' if it exists
                    for col_idx, header in enumerate(header_row):
                        if header.lower() == 'firstlogin':
                            sheet.update_cell(row_index, col_idx + 1, 'No')
                            break
                
                return jsonify({
                    "success": True, 
                    "message": "Password updated successfully"
                })
            except Exception as sheets_error:
                print(f"❌ Google Sheets error, using fallback: {sheets_error}")
        
        # Fallback mode
        print("🔄 Using fallback password update")
        
        if email not in FALLBACK_USERS:
            return jsonify({"success": False, "error": "User not found"}), 404
        
        # In fallback mode, update the in-memory user data
        FALLBACK_USERS[email]["password"] = new_password
        FALLBACK_USERS[email]["first_time"] = False
        
        return jsonify({
            "success": True, 
            "message": "Password updated successfully (fallback mode)"
        })

    except Exception as e:
        print(f"❌ Update password error: {e}")
        return jsonify({"success": False, "error": "Server error during password update"}), 500


# --- IMAGE GENERATION ENDPOINT ---


@app.route("/generate-image", methods=["POST"])
def generate_image_api():
   if "image" not in request.files:
       return jsonify({"error": "No image uploaded"}), 400


   file = request.files["image"]
   img_stream = io.BytesIO(file.read())
   img_stream.seek(0)
   try:
       uploaded_image = Image.open(img_stream).convert("RGB")
   except Exception as e:
       return jsonify({"error": f"Invalid image file: {str(e)}"}), 400


   try:
       style_index = int(request.form.get("style_index", -1))
   except ValueError:
       return jsonify({"error": "Invalid style_index"}), 400


   if not (0 <= style_index < len(PROMPT_FUNCTIONS)):
       return jsonify({"error": "style_index out of range"}), 400


   attributes_str = request.form.get("attributes", "{}")
   try:
       attributes = json.loads(attributes_str)
   except json.JSONDecodeError:
       return jsonify({"error": "Invalid attributes JSON"}), 400


   prompt_template = PROMPT_FUNCTIONS[style_index]()
   final_prompt = replace_placeholders(prompt_template, attributes)


   try:
       full_prompt = (
           "Transform this photo photorealistically for premium e-commerce quality. "
           f"Instructions: {final_prompt} Avoid distortion, blur, watermarks, or cropping."
       )


       response = image_model.generate_content(
           [uploaded_image, full_prompt],
           generation_config=genai.types.GenerationConfig(
               temperature=0.6, top_p=0.9, top_k=40
           ),
       )


       found_image = False
       for part in response.candidates[0].content.parts:
           if hasattr(part, "inline_data") and part.inline_data and part.inline_data.mime_type.startswith("image/"):
               image_bytes = part.inline_data.data
               img = Image.open(io.BytesIO(image_bytes))
               unique_filename = f"generated_{uuid.uuid4().hex}.jpg"
               local_path = os.path.join(OUTPUT_DIR, unique_filename)
               img.save(local_path, format='JPEG', quality=95, optimize=True)


               gcs_url = None
               try:
                   if storage_client:
                       gcs_blob_name = f"generated/{unique_filename}"
                       gcs_url = upload_to_gcs(local_path, gcs_blob_name)
                   else:
                       print("âš  GCS client not available, skipping upload")
               except Exception as gcs_error:
                   print(f"âš  GCS upload failed: {gcs_error}")


               preview_url = request.host_url.rstrip('/') + '/generated_images/' + unique_filename


               found_image = True
               return jsonify({
                   "success": True,
                   "filename": unique_filename,
                   "gcs_url": gcs_url,
                   "preview_url": preview_url,
                   "file_size": os.path.getsize(local_path),
                   "image_size": f"{img.width}x{img.height}",
                   "style_index": style_index
               }), 200


       if not found_image:
           return jsonify({"error": "No image returned from model."}), 500
   except Exception as e:
       import traceback
       print(traceback.format_exc())
       return jsonify({"error": f"Generation/Upload failed: {str(e)}"}), 500


@app.route("/generated_images/<filename>")
def serve_generated_image(filename):
   """Serve generated images securely"""
   try:
       file_path = os.path.join(OUTPUT_DIR, filename)
       if not os.path.exists(file_path):
           return jsonify({"error": "Image file not found"}), 404
       return send_file(file_path, mimetype='image/jpeg')
   except Exception as e:
       return jsonify({"error": f"Error serving image: {str(e)}"}), 500


@app.route("/api/debug-images")
def debug_images():
   """Debug endpoint to list generated images info"""
   try:
       files = os.listdir(OUTPUT_DIR)
       file_info = []
       for file in files:
           file_path = os.path.join(OUTPUT_DIR, file)
           file_info.append({
               'name': file,
               'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
               'exists': os.path.exists(file_path)
           })
       return jsonify({
           "output_dir": OUTPUT_DIR,
           "absolute_path": os.path.abspath(OUTPUT_DIR),
           "files": file_info
       })
   except Exception as e:
       return jsonify({"error": str(e)}), 500


# --- TEXT GENERATION HELPERS ---


def create_base_prompt(subcategory, product_details, task_type):
   if task_type == 'name':
       instruction = "TASK: Write exactly one labeled line: Product Name: [title here]"
   else:
       instruction = "TASK: Write exactly one labeled line: Product Description: [description here]"
   return f"""
You are an expert Amazon e-commerce copywriter specializing in Clothing.
Generate a {'product title' if task_type == 'name' else 'product description'} based on the provided details.
{instruction}


Available Product Information:
Subcategory: {subcategory}
{product_details if product_details else 'No additional details provided'}


IMPORTANT:
- For title: Max 200 characters, include key features
- For description: Max 2000 characters, focus on material, fit, and benefits
- Use factual information only from the provided details
- If details are limited, create a professional generic description
- No promotional language, be factual and descriptive
- End description with a complete sentence


EXAMPLES:
Even with minimal information, create professional output:


Input:
Subcategory: T-Shirt
Brand: Generic Brand
Material: Cotton


Output for title:
Product Name: Generic Brand Cotton T-Shirt | Comfortable Casual Wear


Output for description:
Product Description: This cotton t-shirt from Generic Brand offers comfortable everyday wear. Made from soft cotton material, it provides breathability and ease of movement. The classic design makes it suitable for various casual occasions.


Subcategory: {subcategory}
Details: {product_details if product_details else 'Basic clothing item'}
"""


def call_gemini(prompt, max_tokens):
   try:
       response = text_model.generate_content(
           prompt,
           generation_config=types.GenerationConfig(
               temperature=0.8,
               max_output_tokens=max_tokens,
           ),
       )
       if not response.candidates:
           return "Generation Failed: Model returned no candidates/output."


       candidate = response.candidates[0]
       finish_reason = candidate.finish_reason


       FINISH_REASON_SAFETY = 2
       FINISH_REASON_STOP = 1


       if finish_reason == FINISH_REASON_SAFETY:
           blocked_category_name = ""
           if candidate.safety_ratings:
               try:
                   blocked_category_name = candidate.safety_ratings[0].category.name
               except AttributeError:
                   blocked_category_name = f"Code {candidate.safety_ratings[0].category}"
           return f"Generation Failed: Output Blocked by Safety Filters (Finish Reason: SAFETY). Blocked Category: {blocked_category_name}"


       if finish_reason == FINISH_REASON_STOP and hasattr(response, "text") and response.text:
           return response.text.strip()


       return "Generation Failed: Model stopped with non-success reason."
   except Exception as e:
       return f"Generation Failed: API Error. {type(e).__name__} - {str(e)}"


def generate_product_name(subcategory, product_details):
   prompt = create_base_prompt(subcategory, product_details, 'name')
   raw_output = call_gemini(prompt, 2000)
   label = "Product Name:"
   if raw_output.startswith(label):
       return raw_output[len(label):].strip()
   return raw_output


def generate_product_description(subcategory, product_details):
   prompt = create_base_prompt(subcategory, product_details, 'description')
   raw_output = call_gemini(prompt, 2000)
   label = "Product Description:"
   if raw_output.startswith(label):
       return raw_output[len(label):].strip()
   return raw_output


# --- TEXT GENERATION ENDPOINT ---


@app.route('/api/generate-title-description', methods=['POST'])
def generate_title_description():
   try:
       data = request.get_json()
       print(f"ðŸ“ Received text generation request: {data}")


       if not data:
           return jsonify({'success': False, 'error': 'No data provided'}), 400


       subcategory = data.get('subcategory', '')
       task_type = data.get('type', 'title')


       product_details_lines = []


       for k, v in data.items():
           if k not in ('subcategory', 'type') and v is not None:
               cleaned_v = str(v).strip()
               if cleaned_v and cleaned_v != 'N/A' and cleaned_v != 'null':
                   product_details_lines.append(f"{k}: {cleaned_v}")


       product_details = "\n".join(product_details_lines)


       print(f"ðŸ” Processed data - Subcategory: '{subcategory}', Details lines: {len(product_details_lines)}")
       print(f"ðŸ“‹ Product details: {product_details}")


       if not subcategory:
           if 'Generic Name' in data:
               subcategory = data.get('Generic Name', '')
           elif 'Product Type' in data:
               subcategory = data.get('Product Type', '')
           elif 'Category' in data:
               subcategory = data.get('Category', '')


       if not subcategory:
           subcategory = "Clothing Item"
           print("âš  No subcategory found, using default")


       if not product_details and len(product_details_lines) == 0:
           print("âœ— No valid product details found after cleaning")
           minimal_details = []
           for k, v in data.items():
               if k not in ('subcategory', 'type') and v:
                   minimal_details.append(f"{k}: {v}")


           if minimal_details:
               product_details = "\n".join(minimal_details)
               print(f"âš¡ Using minimal details: {product_details}")
           else:
               return jsonify({
                   'success': False,
                   'error': 'Please provide at least some product details like Brand, Material, Fit, etc.'
               }), 400


       print(f"âœ“ Final - Subcategory: '{subcategory}', Details count: {len(product_details_lines)}")


       if task_type == 'title':
           generated_title = generate_product_name(subcategory, product_details)
           if generated_title.startswith("Generation Failed:"):
               return jsonify({'success': False, 'error': generated_title}), 500
           return jsonify({'success': True, 'generated_title': generated_title})


       elif task_type == 'description':
           generated_description = generate_product_description(subcategory, product_details)
           if generated_description.startswith("Generation Failed:"):
               return jsonify({'success': False, 'error': generated_description}), 500
           return jsonify({'success': True, 'generated_description': generated_description})


       else:
           return jsonify({'success': False, 'error': 'Unknown type specified'}), 400


   except Exception as e:
       import traceback
       print(traceback.format_exc())
       return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500




if __name__ == "__main__":

    import sys
    print("✅ Flask app initialized successfully", file=sys.stderr, flush=True)
    print(f"🚀 Starting Flask on port {os.environ.get('PORT', 8080)} ...", file=sys.stderr, flush=True)


    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)



