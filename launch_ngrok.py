import os
import subprocess
from dotenv import load_dotenv

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    ngrok_domain = os.environ.get("NGROK_DOMAIN", "msm-workflow.ngrok-free.app")
    django_port = os.environ.get("DJANGO_PORT", "8000")
    
    # Start ngrok with the custom domain
    subprocess.run(["ngrok", "http", f"--domain={ngrok_domain}", django_port])

if __name__ == "__main__":
    main()