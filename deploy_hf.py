import os
from huggingface_hub import HfApi, create_repo

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("Set HF_TOKEN environment variable before running this script.")
REPO_ID = "kartikaneja5/sre-incident-response"
SPACE_SDK = "docker"

api = HfApi(token=HF_TOKEN)

# 1. Create the Space (Docker-based)
print(f"[1/2] Creating HuggingFace Space: {REPO_ID} ...")
try:
    url = create_repo(
        repo_id=REPO_ID,
        repo_type="space",
        space_sdk=SPACE_SDK,
        token=HF_TOKEN,
        exist_ok=True,
        private=False,
    )
    print(f"  Space URL: {url}")
except Exception as e:
    print(f"  Space may already exist: {e}")

# 2. Upload the project files
print(f"[2/2] Uploading project files ...")

# Files and folders to upload
IGNORE_PATTERNS = [
    "venv/**",
    ".venv/**",
    "__pycache__/**",
    ".git/**",
    ".env",
    "*.pyc",
    "deploy_hf.py",
]

api.upload_folder(
    folder_path=".",
    repo_id=REPO_ID,
    repo_type="space",
    ignore_patterns=IGNORE_PATTERNS,
    commit_message="Deploy SRE Incident Response environment",
    token=HF_TOKEN,
)

print(f"\n✅ Deployment complete!")
print(f"🌐 Space URL: https://huggingface.co/spaces/{REPO_ID}")
