import urllib.request
import json
import os
import ssl

ctx = ssl.create_default_context()
api = "https://api.github.com/repos/yt-dlp/ejs/releases/latest"
req = urllib.request.Request(api, headers={"User-Agent": "DockerBuild"})
data = json.loads(urllib.request.urlopen(req, context=ctx).read())

tag = data["tag_name"]
print(f"EJS Release: {tag}")

cache_dir = "/root/.cache/yt-dlp/ytdlp-ejs"
os.makedirs(cache_dir, exist_ok=True)

downloaded = 0
for asset in data["assets"]:
    name = asset["name"]
    if name.endswith(".js"):
        url = asset["browser_download_url"]
        dest = os.path.join(cache_dir, name)
        print(f"Downloading {name} ({asset['size']} bytes expected)...")
        urllib.request.urlretrieve(url, dest)
        actual_size = os.path.getsize(dest)
        print(f"  Saved: {actual_size} bytes")
        if actual_size < 1000:
            print(f"  ⚠️ WARNING: File too small!")
        else:
            downloaded += 1

print(f"\n=== EJS Cache ({downloaded} files) ===")
for f in sorted(os.listdir(cache_dir)):
    fp = os.path.join(cache_dir, f)
    print(f"  {f}: {os.path.getsize(fp)} bytes")

if downloaded == 0:
    print("❌ NO EJS FILES!")
    exit(1)
