import sys
import json
import tomllib
import zipfile
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ModInfo:
    file: str
    loaders: list
    name: str = "Unknown"
    version: str = "Unknown"
    minecraft: str = "Unknown"


def read_mod(jar):
    with zipfile.ZipFile(jar) as z:
        names = z.namelist()

        #Figure out which loaders this jar supports
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


folder = Path(sys.argv[1])
if not folder.exists():
    print(f"Folder {folder} does not exist")
    sys.exit(1)

jars = list(folder.glob("*.jar"))
print("Found", len(jars), "mods")

for jar in jars:
    mod = read_mod(jar)
    print(mod)