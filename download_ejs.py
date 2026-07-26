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

for asset in data["assets"]:
    name = asset["name"]
    if name.endswith(".js"):
        url = asset["browser_download_url"]
        dest = os.path.join(cache_dir, name)
        print(f"Downloading {name} from {url} ...")
        urllib.request.urlretrieve(url, dest)
        size = os.path.getsize(dest)
        print(f"  OK: {size} bytes")

print("=== EJS Cache ===")
for f in os.listdir(cache_dir):
    fp = os.path.join(cache_dir, f)
    print(f"  {f}: {os.path.getsize(fp)} bytes")
