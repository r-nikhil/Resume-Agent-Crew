# from langtrace_python_sdk import langtrace

# langtrace.init(api_key = 'be02fc1d0896d5fc57bde3496ac7d159e895b6723037b9ba5ac6d91f66413eb7')

from flask import Flask, render_template, request, jsonify, send_file
from thralla_boys.crew import ThrallaBoys
import os
import threading
import queue
from datetime import datetime
import logging
import sys
from io import StringIO

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Queue for storing logs
log_queue = queue.Queue()
current_process = None

class LogCapture:
    """Custom class to capture and manage logs"""
    def __init__(self, queue):
        self.queue = queue
        self.stdout = sys.stdout
        self.string_buffer = StringIO()

    def write(self, message):
        if message.strip():  # Only process non-empty messages
            self.queue.put({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'message': message.strip()
            })
        self.stdout.write(message)
        self.string_buffer.write(message)

    def flush(self):
        self.stdout.flush()
        self.string_buffer.flush()

def log_handler(message):
    """Handle incoming log messages"""
    log_queue.put({
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'message': message
    })

def run_crew_ai(resume_path, job_url):
    """Run the CrewAI process"""
    try:
        # Redirect stdout to capture logs
        sys.stdout = LogCapture(log_queue)

        # Prepare inputs for the crew
        inputs = {
            'resume_path': resume_path,
            'job_url': job_url
        }

        # Create and run the crew
        crew = ThrallaBoys().crew()
        result = crew.kickoff(inputs=inputs)

        # Extract the output content
        output_content = result.raw if hasattr(result, 'raw') else str(result)

        # Ensure output directory exists and save the result
        output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'analysis.md')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)

        # Signal completion
        log_handler("ANALYSIS_COMPLETE")

    except Exception as e:
        log_handler(f"Error occurred: {str(e)}")
        logger.error(f"Error in run_crew_ai: {str(e)}")
    finally:
        # Restore stdout
        sys.stdout = sys.__stdout__

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    """Handle form submission"""
    try:
        # Get form data
        resume_file = request.files['resume']
        job_url = request.form['job_url']

        # Create uploads directory if it doesn't exist
        uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)

        # Save the resume file
        resume_path = os.path.join(uploads_dir, 'resume.md')
        resume_file.save(resume_path)

        # Clear existing logs
        while not log_queue.empty():
            log_queue.get()

        # Start the CrewAI process in a separate thread
        global current_process
        current_process = threading.Thread(
            target=run_crew_ai,
            args=(resume_path, job_url)
        )
        current_process.start()

        return jsonify({
            'status': 'success',
            'message': 'Analysis process started successfully'
        })

    except Exception as e:
        logger.error(f"Error in submit: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error starting analysis: {str(e)}'
        }), 500

@app.route('/logs')
def get_logs():
    """Return any new logs"""
    try:
        logs = []
        while not log_queue.empty():
            logs.append(log_queue.get())
        return jsonify(logs)
    except Exception as e:
        logger.error(f"Error in get_logs: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving logs: {str(e)}'
        }), 500

@app.route('/download')
def download_result():
    """Download the generated markdown file"""
    try:
        output_path = os.path.join(os.path.dirname(__file__), 'outputs', 'analysis.md')

        if not os.path.exists(output_path):
            return jsonify({
                'status': 'error',
                'message': 'Analysis file not found. Please run the analysis first.'
            }), 404

        return send_file(
            output_path,
            mimetype='text/markdown',
            as_attachment=True,
            download_name='analysis.md'
        )
    except Exception as e:
        logger.error(f"Error in download_result: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error downloading file: {str(e)}'
        }), 500

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return jsonify({
        'status': 'error',
        'message': 'Resource not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500

# Add cleanup of temporary files
def cleanup_temp_files():
    """Clean up temporary files"""
    try:
        uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
        for file in os.listdir(uploads_dir):
            file_path = os.path.join(uploads_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
    except Exception as e:
        logger.error(f"Error cleaning up temporary files: {str(e)}")

if __name__ == '__main__':
    # Ensure required directories exist
    for directory in ['uploads', 'outputs']:
        os.makedirs(os.path.join(os.path.dirname(__file__), directory), exist_ok=True)

    # Run the Flask app
    app.run(port=5001,debug=True)