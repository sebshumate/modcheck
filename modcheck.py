import sys
import json
import tomllib
import zipfile
import hashlib
import requests
from pathlib import Path
from dataclasses import dataclass
import argparse


@dataclass
class ModInfo:
    file: str
    loaders: list
    name: str = "Unknown"
    version: str = "Unknown"
    minecraft: str = "Unknown"
    sha1: str = ""


def read_mod(jar):
    with zipfile.ZipFile(jar) as z:
        names = z.namelist()

        # Figure out which loaders this jar supports
        loaders = []
        if "fabric.mod.json" in names:
            loaders.append("fabric")
        if "META-INF/neoforge.mods.toml" in names:
            loaders.append("neoforge")
        if "META-INF/mods.toml" in names:
            loaders.append("forge")
        if not loaders:
            loaders.append("unknown")

        mod = ModInfo(file=jar.name, loaders=loaders)
        mod.sha1 = hashlib.sha1(jar.read_bytes()).hexdigest()

        # Fabric mods: read fabric.mod.json
        if "fabric.mod.json" in names:
            data = json.loads(z.read("fabric.mod.json"), strict=False)
            mod.name = data.get("name")
            mod.version = data.get("version")
            mod.minecraft = data.get("depends", {}).get("minecraft")

        # Forge/NeoForge mods: read the TOML file
        toml_file = None
        if "META-INF/neoforge.mods.toml" in names:
            toml_file = "META-INF/neoforge.mods.toml"
        elif "META-INF/mods.toml" in names:
            toml_file = "META-INF/mods.toml"

        if toml_file and "fabric.mod.json" not in names:
            info = tomllib.loads(z.read(toml_file).decode("utf-8"))
            entry = info["mods"][0]
            mod.name = entry.get("displayName")
            mod.version = entry.get("version")

            mod_id = entry.get("modId")
            for dep in info.get("dependencies", {}).get(mod_id, []):
                if dep.get("modId") == "minecraft":
                    mod.minecraft = dep.get("versionRange")

    return mod


HEADERS = {"User-Agent": "sebshumate/modcheck/0.1 (github.com/sebshumate/modcheck)"}


def lookup(sha1):
    url = f"https://api.modrinth.com/v2/version_file/{sha1}?algorithm=sha1"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 404:
        return None
    return response.json()

def check_update(mod, mc_version):
    url = f"https://api.modrinth.com/v2/version_file/{mod.sha1}/update?algorithm=sha1"
    body = {"loaders": mod.loaders, "game_versions": [mc_version]}
    response = requests.post(url, json=body, headers=HEADERS)
    if response.status_code == 404:
        return None
    return response.json()

def project_name(project_id):
    url = f"https://api.modrinth.com/v2/project/{project_id}"
    return requests.get(url, headers=HEADERS).json().get("title", project_id)

# Main program 

parser = argparse.ArgumentParser(description="Check a Minecraft mods folder for updates")
parser.add_argument("folder", help="path to your mods folder")
parser.add_argument("--mc", default="26.3", help="Minecraft version, e.g. 1.21.1")
args = parser.parse_args()

folder = Path(args.folder)
if not folder.exists():
    print(f"Folder {folder} does not exist")
    sys.exit(1)

jars = list(folder.glob("*.jar"))
print("Found", len(jars), "mods")

installed = set()
required = set()

for jar in jars:
    mod = read_mod(jar)
    result = lookup(mod.sha1)
    if result is None:
        print(mod.name, "-> not on Modrinth")
    else:
        print(mod.name, "->", result["version_number"], result["game_versions"])
        installed.add(result["project_id"])
        for dep in result["dependencies"]:
            if dep["dependency_type"] == "required" and dep["project_id"]:
                required.add(dep["project_id"])

    latest = check_update(mod, args.mc)
    if latest is None:
        print("  No version for", args.mc)
    elif args.mc not in result["game_versions"]:
        print("  WRONG GAME VERSION: built for", result["game_versions"], "-> get", latest["version_number"])
    elif latest["version_number"] == result["version_number"]:
        print("  Up to date")
    else:
        print("  UPDATE:", result["version_number"], "->", latest["version_number"])
    print()

missing = required - installed
for project_id in missing:
    print("MISSING DEPENDENCY:", project_name(project_id))
    
    print()